#!/usr/local/bin/python
#
# Light Server, to replace the connectport
#
from xbee import ZigBee
from serial import Serial
from flask import Flask
from flask import render_template
from flask import jsonify
from flask import request,redirect,url_for
import struct, re, threading, time, logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

app = Flask(__name__)
nodes = {}
xbee = None
localNodeH = []
localNodeL = []

expr = re.compile('Qr(\d+)g(\d+)b(\d+)s(\d+)\r\n.*r(\d+)g(\d+)b(\d+)\r\n', re.M)

def sendToNode(node,data,frame_id='A'):
    logger.debug("sending %s to %s", data, node['string_address'])
    xbee.send("tx", dest_addr_long=node['address'], dest_addr='\xff\xfe', data=data, frame_id=frame_id)

def atToNode(node,command,parameter,frame_id='B'):
    logger.debug("sending %s %s to %s", command, parameter, node['string_address'])
    xbee.remote_at(command=command, parameter=parameter, dest_addr_long=node['address'], frame_id=frame_id)
    
@app.route('/lights')
def lights():
    logger.debug(request.args.to_dict())
    for nodekey in nodes.keys():
        node = nodes[nodekey]
        key=node['name']+"_color"
        key2=node['name']+"_color2"
        if key in request.args:
            # this can probably be done more simply
            newcolor = struct.unpack('4B',struct.pack('>L',int(request.args[key],16)))[1:]
            newcolor2 = newcolor
            if key2 in request.args:
                newcolor2 = struct.unpack('4B',struct.pack('>L',int(request.args[key2],16)))[1:]
                node['colorvalue2'] = request.args[key2]
            cmd = 'A'
            if newcolor != newcolor2: 
                cmd = 'F'
            if ('color' not in node and sum(newcolor) > 0) or ('color' in node and node['color'] != newcolor):
                node['color'] = newcolor
                node['colorvalue'] = request.args[key]
                sendToNode(node,'{0}r{1}g{2}b{3}\n'.format(cmd,newcolor[0],newcolor[1],newcolor[2]))
            if newcolor != newcolor2 and (('color2' not in node and sum(newcolor2) > 0) or ('color2' in node and node['color2'] != newcolor2)):
                cmd='C'
                sendToNode(node,'{0}r{1}g{2}b{3}\n'.format(cmd,newcolor2[0],newcolor2[1],newcolor2[2]))
            node['color2'] = newcolor2

    return render_template('lights.html',nodes=sorted(nodes.values(), key=lambda n: n['name'].lower()))

@app.route('/')
def index():
    return redirect(url_for('lights'))

@app.route('/query')
def query():
    retnodes=[]
    for key in nodes.keys():
        node = nodes[key]
        retnode = {'address': node['string_address'], 'name': node['name']}
        if 'color' in node:
            retnode['color'] = '{0[0]:02x}{0[1]:02x}{0[2]:02x}'.format(node['color'])
            retnode['color2'] = '{0[0]:02x}{0[1]:02x}{0[2]:02x}'.format(node['color2'])
        retnodes.append(retnode)
    return jsonify(nodes=retnodes)

def add_node(data): 
    logger.debug('%s',data)
    if data['id'] == 'at_response' and data['command'] == 'ND':
        key = '{0:016x}'.format(struct.unpack('>Q',data['parameter']['source_addr_long'])[0])
        if key not in nodes:
            nodes[key] = ({'address': data['parameter']['source_addr_long'], 'string_address': key, 'name': data['parameter']['node_identifier'], 'colorvalue': '000000','colorvalue2': '000000'})
            logger.info(nodes[key])
    elif data['id'] == 'at_response' and data['command'] == 'SH':
        localNodeH[0:] = struct.unpack('4B',data['parameter'])
    elif data['id'] == 'at_response' and data['command'] == 'SL':
        localNodeL[0:] = struct.unpack('4B',data['parameter'])
    elif data['id'] == 'rx':
        parse_query_response(data['source_addr_long'], data['rf_data'])

def parse_query_response(source_addr, data):
    if data[0] != 'Q': return
    key = '{0:016x}'.format(struct.unpack('>Q',source_addr)[0])
    if key not in nodes: return
    m = expr.match(data)
    if not m: return
    node = nodes[key]
    atToNode(node, command='DH', parameter=struct.pack(">L", 0))
    atToNode(node, command='DL', parameter=struct.pack(">L", 0))
    g = map(int, m.groups())
    node['color'] = g[0:3]
    node['colorvalue'] = '{0[0]:02x}{0[1]:02x}{0[2]:02x}'.format(g)
    node['color2'] = g[4:7]
    node['colorvalue2'] = '{0[4]:02x}{0[5]:02x}{0[6]:02x}'.format(g)
    node['speed'] = g[3]
    logger.info(node)

@app.route('/sequence/<light>',methods=["GET"])
def define_sequence(light):
    node = None
    for key in nodes.keys():
        mynode=nodes[key]
        if mynode['name'] == light: break;
    if node is not None:
        return render_template('sequence.html',node)
    else:
        return redirect(url_for('lights'))

@app.route('/sequence/<light>',methods=["PUT","POST"])
def save_sequence(light):
    pass

def do_queries():
    time.sleep(5)
    while True:
        xbee.send("at",command='ND',frame_id='1')
        if len(localNodeH) and len(localNodeL):
            for key in nodes.keys():
                node = nodes[key]
                logger.debug("Querying %s", node['string_address'])
                atToNode(node,'DH',bytearray(localNodeH))
                atToNode(node,'DL',bytearray(localNodeL))
                sendToNode(node,'AQ')
        else:
            xbee.send("at",command='SH',frame_id='2')
            xbee.send("at",command='SL',frame_id='2')
        time.sleep(30)

def start_callback(xbee):
    print "starting"

if __name__ == '__main__':
    serial_port = Serial('/dev/tty.usbserial-A901LVJC', 9600,rtscts=True)
    xbee = ZigBee(serial_port, callback=add_node, start_callback=start_callback)
    xbee.start()
    xbee.send("at",command='ND',frame_id='1')
    queryThread = threading.Thread(target=do_queries)
    queryThread.daemon = True
    queryThread.start()
    app.run(host='0.0.0.0')
