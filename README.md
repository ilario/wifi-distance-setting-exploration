# Code and data for the wifi distance parameter exploration

This code has been written for testing how harmful is to have a too-large distance setting on the two sides of a wifi link (e.g. if two wifi antennas are 2 km apart, what changes when setting the OpenWrt's wifi distance parameter to 2, 5 or 10 km?).

But it CAN BE USED FOR OPTIMIZING ANY PARAMETER. Just adapt the commands below and indicate the name of the new parameter when running the python analysis script.

The metric employed is the receiving and transmitting data rate, measured with iperf3 --bidir (bidir means that iperf3 is contemporaneously flowing data in both directions).

The scripts include the time indication for running from 1 AM to 8 AM in the CEST time zone, adapt accordingly to your timezone and the timezone of your routers.

## Conceptual timeline for experiment

1. start an iperf3 server on the server node
2. wait until the scheduled time
3. set the distance parameter on the server node and on the client node
4. store the current value of the distance parameter in the log file
4. wait 10 minutes
5. the client runs a 8 minutes long bidirectional iperf3 measurement connecting to the server. Both client and server store the resulting data in the log file (the same data will be present on both)
6. go to the first point and repeat (unless this is the last measurement)
7. copy the data to your local machine and process it using the python script

## Components

### Data acquisition commands

Two commands to run on the node designated to be the iperf3 server. Both included in this readme.

One command to run on the node designated to be the iperf3 client. Included in this readme.


### Data analysis script

One Python3 script that takes the client or the server log and plots it in various ways. Included in the repository, with the name `iperf3-analysis.py`.


### Data from distance parameter exploration

Data adquired by @a-gave over two links and various nights is included, with the related graphics.

Data from both the server and the client nodes is included for completeness, but they should be equivalent (both the client and the server files report the results of the same measurement).

## Data acquisition commands

Both the server and the client do the exact same thing, but iperf3 wants us to select one to be the server and the other to be the client. Choose randomly.

On both nodes, install a few dependencies:

```
opkg update
opkg install iperf3 at
```

**Then, for each node, you have to check if your configuration files are old-style or new-style.**

You can do so with:

```
# grep distance /etc/config/lime-autogen
```

If the output specifies the wifi band, like this:

```
	option distance_2ghz '100'
	option distance_5ghz '1000'
```

then you have the OLD style, included in LibreMesh 2020.1.

If the output does not specify the wifi band (2ghz or 5ghz), like this:

```
	option distance '100'
	option distance '1000'
```

then you have the NEW style, that is currently in use in the development code.


### Commands to run on server node

On the server node start the iperf3 server instance:

```
(iperf3 -s --logfile=/tmp/iperf3-server.log >/dev/null 2>&1 )&
```

Then, if you have the OLD style configuration (see above), launch:

```
for i in $(seq 1 7); do
     hour=$(( ($i+22) % 24));
     echo 'uci set lime-node.wifi.distance_5ghz='2100'; uci commit; lime-config; wifi; echo $(date) $(wifi status | grep distance)  >> /tmp/iperf3-server.log' | at $hour:00;
     echo 'uci set lime-node.wifi.distance_5ghz='5000'; uci commit; lime-config; wifi; echo $(date) $(wifi status | grep distance) >> /tmp/iperf3-server.log' | at $hour:20;
     echo 'uci set lime-node.wifi.distance_5ghz='10000';    uci commit; lime-config; wifi; echo $(date) $(wifi status | grep distance) >> /tmp/iperf3-server.log' | at $hour:40;
done 
```

The first lines determine the hour at which the command will run, adapt to your timezone, considering that the routers usually use UTC as their internal timezone.

Otherwise, if you have the NEW style configuration (see above), launch:

```
uci set 'lime-node.5ghz=lime-wifi-band' ; uci commit lime-node 

for i in $(seq 1 7); do
     hour=$(( ($i+22) % 24));
     echo 'uci set lime-node.5ghz.distance='2100'; uci commit; lime-config; wifi; echo $(date) $(wifi status | grep distance)  >> /tmp/iperf3-server.log' | at $hour:00;
     echo 'uci set lime-node.5ghz.distance='5000'; uci commit; lime-config; wifi; echo $(date) $(wifi status | grep distance) >> /tmp/iperf3-server.log' | at $hour:20;
     echo 'uci set lime-node.5ghz.distance='10000';    uci commit; lime-config; wifi; echo $(date) $(wifi status | grep distance) >> /tmp/iperf3-server.log' | at $hour:40;
done 
```

The first line is for creating a new section in /etc/config/lime-node

The first lines in the for, determine the hour at which the command will run, adapt to your timezone, considering that the routers usually use UTC as their internal timezone.


### Commands to run on client node

If you have the OLD style configuration (see above), launch:

```
for i in $(seq 1 7); do
     hour=$(( ($i+22) % 24));
     echo 'uci set lime-node.wifi.distance_5ghz='2100'; uci commit; lime-config; wifi; sleep 600; echo $(date) $(wifi status | grep distance) >> /tmp/iperf3-client.log; iperf3 -c 10.170.170.196 -t 480 --bidir --logfile=/tmp/iperf3-client.log' | at $hour:00
     echo 'uci set lime-node.wifi.distance_5ghz='5000'; uci commit; lime-config; wifi; sleep 600; echo $(date) $(wifi status | grep distance) >> /tmp/iperf3-client.log; iperf3 -c 10.170.170.196 -t 480 --bidir --logfile=/tmp/iperf3-client.log' | at $hour:20
     echo 'uci set lime-node.wifi.distance_5ghz='10000'; uci commit; lime-config; wifi; sleep 600; echo $(date) $(wifi status | grep distance) >> /tmp/iperf3-client.log; iperf3 -c 10.170.170.196 -t 480 --bidir --logfile=/tmp/iperf3-client.log' | at $hour:40
done 
```

Remember to replace 10.170.170.196 with the IP of the server node.

The first lines determine the hour at which the command will run, make sure to use the same as in the server node command.

Otherwise, if you have the NEW style configuration (see above), launch:

```
uci set 'lime-node.5ghz=lime-wifi-band' ; uci commit lime-node 

for i in $(seq 1 7); do
     hour=$(( ($i+22) % 24));
     echo 'uci set lime-node.5ghz.distance='2100'; uci commit; lime-config; wifi; sleep 600; echo $(date) $(wifi status | grep distance) >> /tmp/iperf3-client.log; iperf3 -c 10.170.170.196 -t 480 --bidir --logfile=/tmp/iperf3-client.log' | at $hour:00
     echo 'uci set lime-node.5ghz.distance='5000'; uci commit; lime-config; wifi; sleep 600; echo $(date) $(wifi status | grep distance) >> /tmp/iperf3-client.log; iperf3 -c 10.170.170.196 -t 480 --bidir --logfile=/tmp/iperf3-client.log' | at $hour:20
     echo 'uci set lime-node.5ghz.distance='10000'; uci commit; lime-config; wifi; sleep 600; echo $(date) $(wifi status | grep distance) >> /tmp/iperf3-client.log; iperf3 -c 10.170.170.196 -t 480 --bidir --logfile=/tmp/iperf3-client.log' | at $hour:40
done 
```

The first line is for creating a new section in /etc/config/lime-node

Remember to replace 10.170.170.196 with the IP of the server node.

The first lines in the for loop, determine the hour at which the command will run, make sure to use the same as in the server node command.

## Data analysis script

The python script `iperf3_log_analysis.py` included in this repository has been tested on Linux and on Windows. Clearly you need to have some distribution of Python installed.

It takes two arguments:
* the name of the parameter that has been explored (e.g. distance)
* the name of a log file (e.g. iperf3-client.log)

Run the script with --help for getting some more examples about how to run the script for analysing multiple files together.
