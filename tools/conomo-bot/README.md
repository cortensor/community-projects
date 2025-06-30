# Conomo-bot
A telegram cortensor node monitor bot.

## Features
* Intelligent notifications: Only receive new messages when something happens according to your settings else the latest message gets just updated. You dont get spammed with notifications and still always have the latest data available.
* Node Status: Always have a overview of your nodes. This includes information like online or offline state, ETH balance, metric warnings and visualization of the health for the last 8 hours.
* Failed transactions: Get notified when a transaction failed including detailed information about it.
* Node stall: Get notified when a node is stall. The last 25 transaction are only pings.
* Metrics on demand: The latest metrics data is just one click away
* Node management: Add, remove, edit labels or list your currently configured nodes.
* Estimated rewards: Shows rewards based on your nodes and bonuses.
* Performance: Shows how you nodes currently perform based on metrics.
* Rank: Shows an overview of all ranks and per node.


## Info
Needs a lot of refactoring ;)

## Installl
```
pip install -r rquirements.txt
```

### Env
Copy ```.env.exmaple``` to ```.env``` and edit all noted variables (tg token, eth api, rpc, ...)

### Patch ether scan client
The currently used ether scan api client is deprecated and has a problem with the Arbiscan migration. This is just a dirty hack! 
Run patch.sh or execute the following command to set the correct api url. You May need to adapt the url_builder.py path for you setup:
```
sed -i '/self.API_URL = self._get_api_url()/c\        self.API_URL = "https://api.etherscan.io/v2/api?chainid=421614" #self._get_api_url()' venv/lib/python3.12/site-packages/aioetherscan/url_builder.py
```

## Run
```
python main.py
```

## Commands
#### /subscribe 
subscribe a node address
#### /unsubscribe 
unsubscribe a node address
#### /nodes
list subscribed node addresses
#### /edit_node_label
edit label of a node
#### /show_metrics 
show metrics for a node address
#### /bonus_roles
set amount of bonus roles
#### /new_nodes
set amount of new nodes in this phase
#### /notifications
notification settings