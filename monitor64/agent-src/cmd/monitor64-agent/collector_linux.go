//go:build linux

package main

import (
	"context"

	"github.com/ipv64net/node64/internal/m64agent"
	"github.com/ipv64net/node64/internal/m64linux"
	"github.com/ipv64net/node64/internal/m64proto"
)

// linuxCollector liest die Werte ueber m64linux (eigener Puffer fuer SMART/Updates).
type linuxCollector struct {
	cache *m64linux.Cache
	root  string
}

func newCollector(root string) m64agent.Collector {
	return &linuxCollector{cache: m64linux.NewCache(), root: root}
}

func (c *linuxCollector) Collect(ctx context.Context, sections []string) *m64proto.Report {
	return m64linux.Collect(ctx, m64linux.Options{Sections: sections, Root: c.root, Cache: c.cache})
}

func (c *linuxCollector) Caps() []string {
	return m64linux.Caps(m64linux.Options{Root: c.root, Cache: c.cache})
}
