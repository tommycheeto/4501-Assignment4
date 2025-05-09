#!/usr/bin/env python3

import heapq
import networkx as nx
import matplotlib.pyplot as plt

class Topology:
    def __init__(self):
        self.adj = {} 

    def add_node(self, node):
        if node not in self.adj:
            self.adj[node] = {}

    def add_link(self, src, dst, weight=1):
        self.add_node(src)
        self.add_node(dst)
        self.adj[src][dst] = weight
        self.adj[dst][src] = weight

    def remove_link(self, src, dst):
        if dst in self.adj.get(src, {}):
            del self.adj[src][dst]
        if src in self.adj.get(dst, {}):
            del self.adj[dst][src]

    def shortest_path(self, src, dst):
        if src not in self.adj or dst not in self.adj:
            return None
        dist = {node: float('inf') for node in self.adj}
        prev = {node: None for node in self.adj}
        dist[src] = 0
        pq = [(0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == dst:
                break
            for v, w in self.adj[u].items():
                alt = dist[u] + w
                if alt < dist[v]:
                    dist[v] = alt
                    prev[v] = u
                    heapq.heappush(pq, (alt, v))
        if dist[dst] == float('inf'):
            return None
        path, u = [], dst
        while u is not None:
            path.append(u)
            u = prev[u]
        return list(reversed(path))

    def second_shortest_path(self, src, dst, primary_path):
        second, best_cost = None, float('inf')
        for i in range(len(primary_path) - 1):
            u, v = primary_path[i], primary_path[i+1]
            w = self.adj[u].get(v)
            self.remove_link(u, v)
            alt = self.shortest_path(src, dst)
            if alt and alt != primary_path:
                cost = sum(self.adj.get(alt[j], {}).get(alt[j+1], 0) for j in range(len(alt)-1))
                if cost < best_cost:
                    second, best_cost = alt, cost
            self.add_link(u, v, w)
        return second

class FlowEntry:
    def __init__(self, dst, next_hop, priority=0):
        self.dst = dst
        self.next_hop = next_hop
        self.priority = priority
    def __str__(self):
        return f"[p={self.priority}] if dst=={self.dst} -> {self.next_hop}"

class Switch:
    def __init__(self, name):
        self.name = name
        self.flow_table = []
    def install_flow(self, fe):
        self.flow_table = [e for e in self.flow_table if e.dst != fe.dst]
        self.flow_table.append(fe)
    def show_flows(self):
        print(f"Switch {self.name} flow table:")
        for fe in sorted(self.flow_table, key=lambda x: -x.priority):
            print("  ", fe)
        if not self.flow_table:
            print("  (empty)")

class SDNController:
    def __init__(self):
        self.topo = Topology()
        self.switches = {}
        self.active_flows = {}
        self.lb_counters = {}
        self.link_util = {}  

    def add_node(self, node):
        self.topo.add_node(node)
        self.switches[node] = Switch(node)
        print(f"Added node {node}")

    def add_link(self, src, dst, weight=1):
        self.topo.add_link(src, dst, weight)
        self.link_util[(src, dst)] = 0
        self.link_util[(dst, src)] = 0
        print(f"Added link {src}<->{dst} w={weight}")

    def remove_link(self, src, dst):
        self.topo.remove_link(src, dst)
        self.link_util.pop((src, dst), None)
        self.link_util.pop((dst, src), None)
        print(f"Link failure simulated: {src}<->{dst}. Reconfiguring flows...")
        self.recompute_flows()

    def inject_flow(self, fid, src, dst, priority=0, critical=False):
        primary = self.topo.shortest_path(src, dst)
        if not primary:
            print(f"No path for flow {fid}")
            return
        backup = self.topo.second_shortest_path(src, dst, primary)
        self.active_flows[fid] = {
            'src': src, 'dst': dst,
            'priority': int(priority), 'critical': critical,
            'primary': primary, 'backup': backup
        }
        print(f"Injected flow {fid}: primary={'->'.join(primary)}")
        if critical and backup:
            print(f"  backup={'->'.join(backup)}")
        self.recompute_flows()

    def recompute_flows(self):
        for sw in self.switches.values():
            sw.flow_table.clear()
        for k in self.link_util:
            self.link_util[k] = 0
        for fid, m in sorted(self.active_flows.items(), key=lambda x: -x[1]['priority']):
            self._install(fid, m)

    def _install(self, fid, m):
        src, dst = m['src'], m['dst']
        path = m['primary']
        if m['critical'] and not self.topo.shortest_path(src, dst) and m['backup']:
            path = m['backup']
        elif not m['critical'] and m['backup']:
            key = (src, dst)
            cnt = self.lb_counters.get(key, 0)
            path = m['primary'] if cnt % 2 == 0 else m['backup']
            self.lb_counters[key] = cnt + 1
        print(f"Installing flow {fid} on path {'->'.join(path)} (p={m['priority']})")
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            fe = FlowEntry(dst, v, priority=m['priority'])
            self.switches[u].install_flow(fe)
            self.link_util[(u, v)] += 1

    def show_flows(self):
        for sw in self.switches.values():
            sw.show_flows()

    def query_flow(self, fid):
        if fid not in self.active_flows:
            print(f"No such flow {fid}")
            return
        m = self.active_flows[fid]
        print(f"Flow {fid} -> primary: {'->'.join(m['primary'])}")
        if m['backup']:
            print(f"             backup: {'->'.join(m['backup'])}")

    def query_route(self, src, dst):
        p = self.topo.shortest_path(src, dst)
        print(f"Shortest path {src}->{dst}: {'->'.join(p) if p else 'none'}")

    def visualize(self):
        G = nx.Graph()
        for u, nbrs in self.topo.adj.items():
            for v, w in nbrs.items():
                G.add_edge(u, v, weight=w, util=self.link_util.get((u, v), 0))
        pos = nx.spring_layout(G)
        plt.figure(figsize=(8, 6))
        nx.draw_networkx_nodes(G, pos, node_size=700)
        nx.draw_networkx_labels(G, pos)
        widths = [1 + G[u][v]['util'] * 0.5 for u, v in G.edges()]
        nx.draw_networkx_edges(G, pos, width=widths)
        labels = {(u, v): G[u][v]['util'] for u, v in G.edges()}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
        plt.title("Topology & Link Utilization (#flows)")
        plt.axis('off')
        try:
            plt.show()
        except Exception:
            out = 'topology.png'
            plt.savefig(out)
            print(f'No display available—saved visualization to {out}')
        print("Active flows:")
        for fid, m in self.active_flows.items():
            print(f" {fid}: {'->'.join(m['primary'])} prio={m['priority']} crit={m['critical']}")
        print("Link utilization stats:")
        for (u, v), c in self.link_util.items():
            print(f" {u}->{v}: {c}")

def main():
    ctrl = SDNController()
    greeting = "SDN Controller CLI. Type 'help' for commands."  
    help_text = (
        "Commands:\n"
        "  add_node <node>\n"
        "  add_link <src> <dst> [weight]\n"
        "  simulate_failure <src> <dst>\n"
        "  inject_flow <id> <src> <dst> [priority] [critical]\n"
        "  show_flows\n"
        "  query_flow <id>\n"
        "  query_route <src> <dst>\n"
        "  visualize\n"
        "  exit"
    )
    print(greeting)
    print(help_text)
    while True:
        try:
            parts = input('> ').strip().split()
        except EOFError:
            break
        if not parts:
            continue
        cmd, args = parts[0], parts[1:]
        if cmd == 'exit':
            break
        if cmd == 'help':
            print(help_text)
        elif cmd == 'add_node' and len(args) == 1:
            ctrl.add_node(args[0])
        elif cmd == 'add_link' and 2 <= len(args) <= 3:
            w = int(args[2]) if len(args) == 3 else 1
            ctrl.add_link(args[0], args[1], w)
        elif cmd == 'simulate_failure' and len(args) == 2:
            ctrl.remove_link(args[0], args[1])
        elif cmd == 'inject_flow' and len(args) >= 3:
            fid, src, dst = args[:3]
            prio = int(args[3]) if len(args) >= 4 else 0
            crit = (args[4].lower() == 'true') if len(args) >= 5 else False
            ctrl.inject_flow(fid, src, dst, prio, crit)
        elif cmd == 'show_flows':
            ctrl.show_flows()
        elif cmd == 'query_flow' and len(args) == 1:
            ctrl.query_flow(args[0])
        elif cmd == 'query_route' and len(args) == 2:
            ctrl.query_route(args[0], args[1])
        elif cmd == 'visualize':
            ctrl.visualize()
        else:
            print("Unknown command. Type 'help'")

if __name__ == '__main__':
    main()



