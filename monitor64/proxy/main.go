// monitor64-dockerproxy: read-only Docker-API über TLS für Monitor64.
//
// Der Proxy bekommt vom Supervisor die read-only Docker-API (docker_api: true), erzeugt
// beim ersten Start CA, Server- und Client-Zertifikat, verlangt ein Client-Zertifikat und
// lässt nur GET/HEAD auf eine feste Pfadliste zu. Beim Start stehen Zugangsdaten und
// SHA-256-Fingerabdruck des Server-Zertifikats im Log.
package main

import (
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"errors"
	"flag"
	"fmt"
	"log"
	"math/big"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/signal"
	"path/filepath"
	"regexp"
	"strings"
	"syscall"
	"time"
)

// erlaubte Pfade: was das Monitor64-Modul Docker abfragt. Alles andere wird abgewiesen.
var allowedPaths = []*regexp.Regexp{
	regexp.MustCompile(`^/_ping$`),
	regexp.MustCompile(`^/version$`),
	regexp.MustCompile(`^/info$`),
	regexp.MustCompile(`^/containers/json$`),
	regexp.MustCompile(`^/containers/[A-Za-z0-9][A-Za-z0-9_.-]*/json$`),
	regexp.MustCompile(`^/containers/[A-Za-z0-9][A-Za-z0-9_.-]*/stats$`),
}

type certs struct {
	dir        string
	caPEM      []byte
	serverCert tls.Certificate
	clientPEM  []byte
	clientKey  []byte
	leaf       *x509.Certificate
}

func main() {
	listen := flag.String("listen", ":2376", "listen address")
	socket := flag.String("socket", "/var/run/docker.sock", "Docker API unix socket")
	dataDir := flag.String("data", "/data/proxy", "directory for certificates")
	flag.Parse()

	log.SetFlags(0)
	log.SetPrefix("monitor64-dockerproxy: ")

	if _, err := os.Stat(*socket); err != nil {
		log.Fatalf("docker socket %s: %v", *socket, err)
	}
	if err := os.MkdirAll(*dataDir, 0o700); err != nil {
		log.Fatalf("data dir: %v", err)
	}
	c, err := ensureCerts(*dataDir)
	if err != nil {
		log.Fatalf("certificates: %v", err)
	}

	fp := sha256.Sum256(c.leaf.Raw)
	creds, _ := json.Marshal(map[string]string{
		"key":  string(c.clientKey),
		"cert": string(c.clientPEM),
		"ca":   string(c.caPEM),
	})
	log.Printf("listen=%s socket=%s", *listen, *socket)
	log.Printf("fingerprint=%s", hex.EncodeToString(fp[:]))
	log.Printf("credentials=%s", creds)

	caPool := x509.NewCertPool()
	if !caPool.AppendCertsFromPEM(c.caPEM) {
		log.Fatalf("ca certificate not usable")
	}
	cfg := &tls.Config{
		MinVersion:   tls.VersionTLS12,
		Certificates: []tls.Certificate{c.serverCert},
		ClientAuth:   tls.RequireAndVerifyClientCert,
		ClientCAs:    caPool,
	}

	proxy := httputil.NewSingleHostReverseProxy(&url.URL{Scheme: "http", Host: "docker"})
	proxy.Transport = &http.Transport{
		DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
			var d net.Dialer
			return d.DialContext(ctx, "unix", *socket)
		},
		MaxIdleConns:    4,
		IdleConnTimeout: 30 * time.Second,
	}

	srv := &http.Server{
		Addr:              *listen,
		Handler:           filter(proxy),
		TLSConfig:         cfg,
		ReadHeaderTimeout: 10 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer stop()
	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutdownCtx)
	}()

	if err := srv.ListenAndServeTLS("", ""); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatalf("listen: %v", err)
	}
}

// filter lässt nur read-only Anfragen auf die erlaubte Pfadliste durch.
func filter(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet && r.Method != http.MethodHead {
			http.Error(w, "forbidden: read-only", http.StatusForbidden)
			return
		}
		for _, re := range allowedPaths {
			if re.MatchString(r.URL.Path) {
				next.ServeHTTP(w, r)
				return
			}
		}
		log.Printf("denied %s %s", r.Method, r.URL.Path)
		http.Error(w, "forbidden: path", http.StatusForbidden)
	})
}

// ensureCerts lädt die Zertifikate aus dir oder erzeugt sie beim ersten Start.
// Vorhandene Dateien werden nie ersetzt: ein neues Zertifikat würde den Pin brechen.
func ensureCerts(dir string) (*certs, error) {
	c := &certs{dir: dir}

	caCertPEM, err := loadOrCreate(filepath.Join(dir, "ca.crt"), func() ([]byte, []byte, error) {
		return newCA(dir)
	})
	if err != nil {
		return nil, err
	}
	caKeyPEM, err := os.ReadFile(filepath.Join(dir, "ca.key"))
	if err != nil {
		return nil, err
	}
	caCert, caKey, err := parseCA(caCertPEM, caKeyPEM)
	if err != nil {
		return nil, err
	}
	c.caPEM = caCertPEM

	serverCertPEM, err := loadOrCreate(filepath.Join(dir, "server.crt"), func() ([]byte, []byte, error) {
		return newLeaf(dir, "server", caCert, caKey, []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth})
	})
	if err != nil {
		return nil, err
	}
	serverKeyPEM, err := os.ReadFile(filepath.Join(dir, "server.key"))
	if err != nil {
		return nil, err
	}
	c.serverCert, err = tls.X509KeyPair(serverCertPEM, serverKeyPEM)
	if err != nil {
		return nil, err
	}
	leaf, err := x509.ParseCertificate(c.serverCert.Certificate[0])
	if err != nil {
		return nil, err
	}
	c.leaf = leaf

	c.clientPEM, err = loadOrCreate(filepath.Join(dir, "client.crt"), func() ([]byte, []byte, error) {
		return newLeaf(dir, "client", caCert, caKey, []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth})
	})
	if err != nil {
		return nil, err
	}
	c.clientKey, err = os.ReadFile(filepath.Join(dir, "client.key"))
	if err != nil {
		return nil, err
	}
	return c, nil
}

// loadOrCreate nutzt die vorhandene Datei oder ruft make auf, das Zertifikat und
// Schlüssel schreibt.
func loadOrCreate(path string, make func() ([]byte, []byte, error)) ([]byte, error) {
	if b, err := os.ReadFile(path); err == nil {
		return b, nil
	}
	certPEM, keyPEM, err := make()
	if err != nil {
		return nil, err
	}
	if err := os.WriteFile(path, certPEM, 0o644); err != nil {
		return nil, err
	}
	keyPath := strings.TrimSuffix(path, ".crt") + ".key"
	if err := os.WriteFile(keyPath, keyPEM, 0o600); err != nil {
		return nil, err
	}
	return certPEM, nil
}

func newCA(dir string) ([]byte, []byte, error) {
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return nil, nil, err
	}
	tmpl := &x509.Certificate{
		SerialNumber:          newSerial(),
		Subject:               pkix.Name{CommonName: "Monitor64 Docker-Proxy CA"},
		NotBefore:             time.Now().Add(-time.Hour),
		NotAfter:              time.Now().AddDate(10, 0, 0),
		IsCA:                  true,
		BasicConstraintsValid: true,
		KeyUsage:              x509.KeyUsageCertSign | x509.KeyUsageDigitalSignature,
	}
	der, err := x509.CreateCertificate(rand.Reader, tmpl, tmpl, &key.PublicKey, key)
	if err != nil {
		return nil, nil, err
	}
	keyPEM, err := pemKey(key)
	if err != nil {
		return nil, nil, err
	}
	return pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}), keyPEM, nil
}

func newLeaf(dir, name string, caCert *x509.Certificate, caKey *ecdsa.PrivateKey, eku []x509.ExtKeyUsage) ([]byte, []byte, error) {
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return nil, nil, err
	}
	tmpl := &x509.Certificate{
		SerialNumber: newSerial(),
		Subject:      pkix.Name{CommonName: "monitor64-dockerproxy-" + name},
		NotBefore:    time.Now().Add(-time.Hour),
		NotAfter:     time.Now().AddDate(5, 0, 0),
		KeyUsage:     x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment,
		ExtKeyUsage:  eku,
	}
	if name == "server" {
		tmpl.DNSNames = []string{"monitor64", "localhost"}
		tmpl.IPAddresses = localIPs()
	}
	der, err := x509.CreateCertificate(rand.Reader, tmpl, caCert, &key.PublicKey, caKey)
	if err != nil {
		return nil, nil, err
	}
	keyPEM, err := pemKey(key)
	if err != nil {
		return nil, nil, err
	}
	return pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}), keyPEM, nil
}

func parseCA(certPEM, keyPEM []byte) (*x509.Certificate, *ecdsa.PrivateKey, error) {
	cb, _ := pem.Decode(certPEM)
	if cb == nil {
		return nil, nil, fmt.Errorf("ca.crt: no PEM")
	}
	cert, err := x509.ParseCertificate(cb.Bytes)
	if err != nil {
		return nil, nil, err
	}
	kb, _ := pem.Decode(keyPEM)
	if kb == nil {
		return nil, nil, fmt.Errorf("ca.key: no PEM")
	}
	key, err := x509.ParseECPrivateKey(kb.Bytes)
	if err != nil {
		return nil, nil, err
	}
	return cert, key, nil
}

func pemKey(key *ecdsa.PrivateKey) ([]byte, error) {
	der, err := x509.MarshalECPrivateKey(key)
	if err != nil {
		return nil, err
	}
	return pem.EncodeToMemory(&pem.Block{Type: "EC PRIVATE KEY", Bytes: der}), nil
}

func newSerial() *big.Int {
	n, err := rand.Int(rand.Reader, new(big.Int).Lsh(big.NewInt(1), 128))
	if err != nil {
		return big.NewInt(time.Now().UnixNano())
	}
	return n
}

func localIPs() []net.IP {
	var out []net.IP
	ifaces, err := net.Interfaces()
	if err != nil {
		return out
	}
	for _, iface := range ifaces {
		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}
		for _, a := range addrs {
			if ipnet, ok := a.(*net.IPNet); ok && !ipnet.IP.IsUnspecified() && !ipnet.IP.IsMulticast() {
				out = append(out, ipnet.IP)
			}
		}
	}
	return out
}
