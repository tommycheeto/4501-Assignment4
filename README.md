# 4501-Assignment4

to run the program type python sdn_controller.py

the sdn commands will pop up as follows
Commands:
  add_node <node>
  add_link <src> <dst> [weight]
  simulate_failure <src> <dst>
  inject_flow <id> <src> <dst> [priority] [critical]
  show_flows
  query_flow <id>
  query_route <src> <dst>
  visualize
  exit

 then type the following commands
> add_node A
> add_node B
> add_link A B 1
> inject_flow f1 A B 0 false
> show_flows
> visualize
