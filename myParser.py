#!/usr/bin python

import sys, re, random, argparse

def getActSize(size):
	Sum = 1
	size = size-1
	while size>0:
		Sum *= 2
		size -= 1
	return Sum

def getNewCode(data):

	newCode = ''
	exist = 0
	compare = 0
	asciiString = "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
	while True:
		newCode += random.choice(asciiString)
		if newCode in data.keys():
			exist += 1
		compare += 1
		if compare>exist: 
			break
	data.update({newCode:{}})
	return newCode

def count_length(l):
	return str(bin(l)[2:])

'''
Count the toggle
	a and b are now's value and last value
1. extend a or b if necessary
2. do xor to each bit with a and b
	sum +=1 when meet 1
3. return sum
'''
def toggle_count(a, b):
	extend = 0
	if len(a)!=len(b):
		if len(a)>len(b):
			extend = len(a)-len(b)
			b = '0'*extend + b
		else:
			extend = len(b)-len(a)
			a = '0'*extend + a
	Sum = 0
	for x,y in zip(a,b):
		s = int(x)^int(y)
		if s==1:
			Sum+=1
	return Sum
def cal_t(l, st, end):
	fl = l.split()
	fl.pop()
	fl.pop(0)
	tscale = ''.join(fl)
	time = 0
	unit = 0
	ts_match = re.compile(r"(\d+)([a-z]+)")
	ts = ts_match.match(tscale)
	if ts!=None:
		time = ts.group(1)
		unit = ts.group(2).lower()
	if unit=='ps':
		st += '000'
		end += '000'
	elif unit=='ms':
		temp = int(st)/1000000
		st = str(temp)
		temp = int(end)/1000000
		end = str(temp)
	elif unit=='us':
		temp = int(st)/1000
		st = str(temp)
		temp = int(end)/1000
		end = str(temp)
	return st, end
def parse_vcd(vcd_file, start_time, end_time, doDiff):
	re_time = re.compile(r"^#(\d+)")				# re obj of '#(time)'
	re_1b_val = re.compile(r"^([01zxZX])(.+)")		# re obj of e.g '0%'
	re_Nb_val = re.compile(r"^[br](\S+)\s+(.+)")	# re obj of e.g 'b0 @', 'b111 #'
	re_info = re.compile(r"^(\s+\S+)+")			# re obj of e.g '	Jun, ...'
	re_t_val = re.compile(r"^([01])([spn]+)")
	re_init = re.compile(r"^[zxZX](.+)")
	re_len = re.compile("^\[\d+\:\d+\]")

	data = {}		# var structure values
	hier = []		# scope hierachy
	time = 0		# each '#(time)'
	before = 0
	index = -1
	write_file = [] # write file list
	checkVars = False
	startWrite = False
	safeList = []	# store clk
	changeList = []	# extend to 32
	c = 0
	sortDict = {}
	checkTime = False

	fh = open(vcd_file, 'r')
	print "Open File!"
	print "Start: %sns, End: %sns"%(start_time, end_time)

	while True:
		line = fh.readline()
		if line =='':		# EOF
			break
		line = line.strip()	# discard \s of head and tail

		if "$date" in line:
			write_file.append(line)
		elif "$timescale" in line:
			st = line
			if not '$end' in line:
				while fh:
					line = fh.readline()
					st += line
					if '$end' in line:
						break
			start_time, end_time = cal_t(st, start_time, end_time)
			print st
			write_file.append(st)
		elif "$version" in line:
			write_file.append(line)
		elif "$enddefinitions" in line:
			write_file.append(line)
		elif "$dumpvars" in line:
			write_file.append(line)
			checkVars = True
		elif "$dumpon" in line:
			write_file.append(line)
		elif "$dumpoff" in line:
			write_file.append(line)
		elif "$dumpall" in line:
			write_file.append(line)
		elif "$scope" in line:
			write_file.append(line)
			hier.append(line.split()[2])	# take the name of scope	
		elif "$upscope" in line:
			write_file.append(line)
			hier.pop()	# pop the scope
		elif "$var" in line:
			ls = line.split()						# assume all on one line
			vType = ls[1]				# type		#	$var reg 1 * data $end
			vSize = ls[2]				# size		#	$var wire 4 ( addr [3:0] $end
			vCode = ls[3]				# code
			vName = " ".join(ls[4:-1])	# name
			vName_2 = "".join(ls[4:-1])
			if ls[5] != '$end':
				vLength = ''.join(ls[5:-1])
			else:
				vLength = '1'
			shortName = ls[4]
			vPath = '/'.join(hier)
			vFullName = vPath + '/' + vName_2
			if vCode not in data:
				data[vCode] = {}
				if 'nets' not in data[vCode]:
					data[vCode]['nets'] = []
				var_struct = {
					'type': vType,
					'shortName': shortName,
					'length': vLength,
					'name': vName,
					'size': vSize,
					'hier': vPath,
					'FullName' : vFullName,
				}
				if var_struct not in data[vCode]['nets']:
					data[vCode]['nets'].append(var_struct)
			else:
				var_struct = {
					'type': vType,
					'shortName': shortName,
					'length': vLength,
					'name': vName,
					'size': vSize,
					'hier': vPath,
					'FullName': vFullName,
				}
				if var_struct not in data[vCode]['nets']:
					data[vCode]['nets'].append(var_struct)
			if 'clk' in str(vName) or 'reset' in str(vName):	# save clk and reset
				safeList.append(vCode)

			temp = "$var %s\t  %s %s\t%s  $end"%(vType, vSize, vCode, str(vName))
			write_file.append(temp)

		elif line.startswith('#'):
			re_time_match = re_time.match(line)
			time = re_time_match.group(1)		# recording #(time)
			if (int(time)>int(end_time)):
				break
			if time=='0':
				write_file.append(line)			# needs to record #0

		elif line.startswith(('0', '1', 'x', 'z', 'b', 'r','X', 'Z')):
			if line.startswith(('0', '1', 'x', 'z', 'X', 'Z')):
				'''
				if checkTime==False:
					t = re_t_val.match(line)
					if t!=None:
						s = "\t%s"%t.group()
						print s
						write_file.append(s)
						checkTime = True
						continue
				else:
				'''
				m = re_1b_val.match(line)
			elif line.startswith(('b', 'r')):
				m = re_Nb_val.match(line)
			value = m.group(1)
			code = m.group(2)
			if 'x' in value or 'z' in value:
				value = '0'
			
			if checkVars:
				if code in changeList:
					p = "b"+ value + " " + code
					write_file.append(p)
				else:
					write_file.append(line)

			if (code in data):					# record time and value (once a time)
				if 'tv' not in data[code]:
					data[code]['tv'] = []
				if 'index' not in data[code]:
					data[code]['index'] = -1
				if 'count' not in data[code]:
					data[code]['count'] = 0
				data[code]['replace'] = False
				index = data[code]['index']
				if index>=0:
					if data[code]['tv'][index][0]==time:
						data[code]['tv'][index][1] = value
					else:
						data[code]['tv'].append([time, value])
						data[code]['index'] += 1
						index = data[code]['index']
				else:
					data[code]['tv'].append([time,value])
					data[code]['index'] += 1
					index = data[code]['index']

		elif line.startswith("$end"):
			write_file.append(line)
			if checkVars:
				checkVars = False
				startWrite = True

		else:						# sth else
			s = "\t%s"%line
			write_file.append(s)

	if startWrite:
		write_file.append("#1")
		t = 0
		clk = ""
		for code in data:
			if code in safeList:
				t = (int(end_time)-1+1)/2 + 1
				clk = code
				s = "0%s"%clk
				write_file.append(s)
			else:
				if 'count' in data[code]:
					for i in range(len(data[code]['tv'])):			# counter
						if int(data[code]['tv'][i][0])>=int(start_time)  and i>=1:
							a = data[code]['tv'][i][1]
							b = data[code]['tv'][i-1][1]
							if str(a)!="x" and str(b)!="x":
								c = toggle_count(str(a),str(b))
								data[code]['count'] += c
								if int(data[code]['tv'][i][0])==int(end_time):
									break
					binCount = count_length(data[code]['count'])	# invert count to binary type
					s = "b%s %s"%(binCount, code)
					write_file.append(s)

		s = "#%s"%str(t)
		write_file.append(s)
		for code in safeList:
			s = "1%s"%code
			write_file.append(s)
		end_time = int(end_time) + 1
		write_file.append("#%s"%end_time)
		

		if doDiff==True:
			return data
		
		# signals renaming
		i = 0
		while(i<len(write_file)):
			statement = write_file[i]
			if 'force_valid' in statement:
				print statement
			if statement.startswith('$var'):
				l = statement.split()
				code = l[3]
				size = getActSize(int(data[code]['nets'][0]['size']))
				count = int(data[code]['count'])
				if data[code]['nets'][0]['length']!='1':
					R = data[code]['nets'][0]['length']
					L = re_len.match(R)
					a = L.group()
					a = a.replace('[','')
					a = a.replace(']','')
					b = a.split(':')
					startBit = b[1]
					endBit = b[0]
				else:
					startBit = '0'
					endBit = '1'
				if int(count)>int(size):
					if int(size)>2 or startBit!='0' :
						newCode = getNewCode(data)
						data[newCode] = {'count':0, 'size':0}
						if data[code]['nets'][0]['length']!='1':
							write_file[i] = '$var %s\t  %s %s\t%s [%s:%s]  $end'%(l[1],l[2],newCode,l[4],endBit,startBit)
						newType = data[code]['nets'][0]['type']
						newSize = data[code]['nets'][0]['size']
					
						newName = l[4] + '_%s__%s'%(endBit, startBit) + ' [31:0]'
						string = '$var %s\t  32 %s\t%s  $end'%(newType, code, newName)
						data[code]['replace'] = True
						write_file.insert(i+1,string)
						i = i + 1
					elif int(size)<=2:
						
						newName = l[4] + ' [31:0]'
						write_file[i] = '$var %s\t  32 %s\t%s  $end'%(l[1],code,newName)
						data[code]['replace'] = True
					
			if statement.startswith('x'):
				rep = re_init.match(statement)
				copyCode = rep.group(1)
				if data[copyCode]['replace']:
					write_file[i] = 'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx %s'%copyCode
			i = i + 1
		
		nameGroup = vcd_file.split('.')
		rc = genRCFile(data)
		genRc = open(nameGroup[0]+'_toggle.rc','w')
		genRc.write("zoom 0.000000 %s\n"%end_time)
		genRc.write("cursor %s\n\n"%(int(end_time)/2+1))
		for each in rc:
			genRc.write("%s\n"%each)
		genRc.close()


	fh.close()
	return data, write_file

def genRCFile(data):
	sortDict = {}
	rc = []
	for each in data:
		if 'count'  in data[each]:
			sortDict[each] = data[each]['count']
		else:
			sortDict[each] = 0
	ot = sorted(sortDict.items(), key=lambda (k,v): v, reverse = True)
	for each in ot:
		co = each[0]

		if 'nets' in data[co]:
			size = data[co]['nets'][0]['length']
			if size!='1':
				st = "addSignal -h 15 -UNSIGNED -HEX  %s"%(data[co]['nets'][0]['FullName'])
			else:
				st = "addSignal -h 15 %s"%(data[co]['nets'][0]['FullName'])
			rc.append(st)
	return rc

def compare(v1, v2, t1, t2):
	wf = []
	d1 = {}
	d2 = {}
	both = []
	doDiff = True
	data_v1 = parse_vcd(v1,t1,t2,doDiff)
	data_v2 = parse_vcd(v2,t1,t2,doDiff)
	st = []
	for code in data_v1:
		if 'count' in data_v1[code]:
			to1 = data_v1[code]['count']
			if 'name' in data_v1[code]['nets'][0]:
				n1 = data_v1[code]['nets'][0]['name']
				d1[n1] = to1
	for corresp in data_v2:
		if 'count'in data_v2[corresp]:
			to2 = data_v2[corresp]['count']
			if 'name' in data_v2[corresp]['nets'][0]:
				n2 = data_v2[corresp]['nets'][0]['name']
				d2[n2] = to2

	for i in d1:
		if i in d2:	
			first = d1[i]
			second = d2[i]
			difference = second - first
		else:
			first = d1[i]
			second = '-'
			difference = first*-1
		if difference != 0:
			if difference>0:
				st = ['%s:\n'%i,'%s: %s\n'%(v1,first),'%s: %s\n'%(v2,second),'Difference: +', '%s'%difference]
			else:
				difference *= -1
				st = ['%s:\n'%i,'%s: %s\n'%(v1,first),'%s: %s\n'%(v2,second),'Difference: -', '%s'%difference]
			both.append(st)
	for j in d2:
		if j not in d1:
			first = '-'
			second = d2[j]
			difference = second
			if difference != 0:
				st = ['%s:\n'%j,'%s: %s\n'%(v1,first),'%s: %s\n'%(v2,second),'Difference: +', '%s'%difference]
				both.append(st)
	wf = sorted(both, key=  lambda x: int(x[4]),reverse=True)
	return wf


def main():

	msg = "myParser.py [-h] [-d vcd_file_1 vcd_file_2] -t start_time end_time [vcd_file]"
	parser = argparse.ArgumentParser(description='myVCDParser', usage=msg)
	parser.add_argument('vcd', nargs='?', action='store', help='The vcd file you want to parse.')
	parser.add_argument('-d', nargs=2, action='store', dest='comp_file', help='Compare two vcd files.')
	parser.add_argument('-t', nargs=2, action='store', dest='t', help='The start time and the end time. (unit: ns)', required=True)

	args = parser.parse_args()
	if args.vcd is None and args.comp_file is None and args.t is not None:
		print parser.print_help()
		parser.error("You must choose an action.")
		return 
	if args.vcd!=None:
		vcd_file, start_time, end_time = args.vcd, args.t[0], args.t[1]
		vcd, genWrite = parse_vcd(vcd_file, start_time, end_time, False)		# vcd = record all time's signals
		nameGroup = vcd_file.split('.')
		newName = nameGroup[0] + '_toggle'
		genf = open(newName+'.vcd','w')
		for each in genWrite:
			genf.write("%s\n"%each)
		genf.close()

		
	elif args.comp_file!=None:
		vcd_file_1, vcd_file_2 = args.comp_file[0], args.comp_file[1]
		start_time, end_time = args.t[0], args.t[1]
		compWrite = compare(vcd_file_1, vcd_file_2, start_time, end_time)
		compf = open('diff.txt','w')
		compf.write("Difference between %s and %s:\n"%(vcd_file_1, vcd_file_2))
		for i in compWrite:
			for j in i:
				compf.write("%s"%j)
			compf.write("\n\n")
	return 

if __name__ == "__main__":
	main()
