#!/usr/bin python

import sys, re, random, argparse, math
import time
'''
Convert binary to decimal
'''
def getActSize(size):
	Sum = 1
	size = int(size)-1
	while size>0:
		Sum *= 2
		size -= 1
	return Sum

'''
Generate a new code for the old signal
'''
def getNewCode(**data):

	newCode = ''
	exist = 0
	compare = 0
	asciiString = "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
	strList = []
	while True:
		randS = random.choice(asciiString)
		strList.append(randS)
		newCode = ''.join(strList)
		#newCode += random.choice(asciiString)
		if newCode in data.keys():
			exist += 1
		compare += 1
		if compare>exist: 
			break
	data.update({newCode:{}})
	return newCode

'''
Convert decimal to binary
'''
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
	la = len(a)
	lb = len(b)
	if la is not lb:
		if la > lb:
			extend = la - lb
			b = '0'*extend + b
		else:
			extend = lb - la
			a = '0'*extend + a
	Sum = 0
	for x,y in zip(a,b):
		s = int(x)^int(y)
		if s==1:
			Sum+=1
	return Sum

'''
Calculate the correct timescale
e.g
	input type is ns, and the vcd file's timescale is ps
	start_time, end_time both *= 1000
'''
def cal_t(l, st, end):
	fl = l.split()
	fl.pop()
	fl.pop(0)
	tscale = ''.join(fl)
	time = 0
	unit = 0
	ts_match = re.compile(r"(\d+)([a-z]+)")
	ts = ts_match.match(tscale)
	if ts is not None:
		time = ts.group(1)
		unit = ts.group(2).lower()
	if unit=='ps':
		st = float(st) * 1000
		end = float(end) * 1000
		
	elif unit=='ms':
		temp = float(st)/1000000
		st = str(temp)
		temp = float(end)/1000000
		end = str(temp)
	elif unit=='us':
		temp = float(st)/1000
		st = str(temp)
		temp = float(end)/1000
		end = str(temp)
	st = int(st)
	end = int(end)
	return str(st), str(end)

'''
vcd file parsing
	Save all signals each time and calculate the toggle count
	Finally, do renaming if the condition is satisfied
'''

def parse_vcd(vcd_file, start_time, end_time, doDiff, mod, ex, threshold, searchstring):

	# regular expression 
	re_time = re.compile(r"^#(\d+)")				# re obj of '#(time)'
	re_1b_val = re.compile(r"^([01zxZX])(.+)")		# re obj of e.g '0%'
	re_Nb_val = re.compile(r"^[br](\S+)\s+(.+)")	# re obj of e.g 'b0 @', 'b111 #'
	re_info = re.compile(r"^(\s+\S+)+")			# re obj of e.g '	Jun, ...'
	re_t_val = re.compile(r"^([01])([spn]+)")
	re_len = re.compile("^(\[\d+\])*(\[\d+\:\d+\])")
	#######################################

	# variables
	data = {}		# var structure values
	hier = []		# scope hierachy
	time = 0		# each '#(time)'
	index = -1
	write_file = [] # write file list
	checkVars = False
	startWrite = False
	safeList = []	# store clk, reset
	changeList = []	# extend to 32
	sortDict = {}	# used to sort in dict
	ifWrite = True
	nameGroup = vcd_file.split('.')
	#######################################
	
	fh = open(vcd_file, 'r')
	print "%s, Start: %sns, End: %sns"%(vcd_file, int(start_time), int(end_time))


	# READLINE
	# DIVIDE TOKEN INTO DIFFERENT STRUCTURE
	while True:
		line = fh.readline()
		if line is '':		# EOF
			break
		line = line.strip()	# discard \s of head and tail

		if "$date" in line or '$version' in line or '$dumpon' in line or '$dumpall' in line or '$dumpoff' in line or '$enddefinitions' in line:
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
			et = 0
			for line in reversed(open(vcd_file).readlines()):
				if line.startswith('#'):
					l = re.match("^#(\d+)",line)
					et = l.group(1)
					break
			if float(et)<=float(start_time) or float(et)<float(end_time):
				print "Time range error."
				sys.exit(-1)
			write_file.append(st)
		elif "$dumpvars" in line:
			write_file.append(line)
			checkVars = True
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
			vName = " ".join(ls[4:-1])	# name connect with ' []'
			vName_2 = "".join(ls[4:-1])	# name connect with '[]'
			if ls[5] != '$end':
				vLength = ''.join(ls[5:-1])
			else:
				vLength = '1'
			shortName = ls[4]
			vPath = '/'.join(hier)
			vFullName = '/'.join([vPath,vName_2])
			if vCode not in data:
				data[vCode] = {}
				if 'nets' not in data[vCode]:
					data[vCode]['nets'] = []
			var_struct = {
				'type': vType,
				'shortName': shortName,
				'length': vLength,
				'name': vName,
				'name_2': vName_2,
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
			if (float(time)>float(end_time)):
				break
			if time is '0':
				write_file.append(line)			# needs to record #0

		elif line.startswith(('0', '1', 'x', 'z', 'b', 'r','X', 'Z')):
			if line.startswith(('0', '1', 'x', 'z', 'X', 'Z')):
				m = re_1b_val.match(line)
			elif line.startswith(('b', 'r')):
				m = re_Nb_val.match(line)
			value = m.group(1)
			code = m.group(2)
			if 'x' in value or 'z' in value:
				value = '0'
			
			# for correct initial
			if checkVars:
				'''
				if code in changeList:
					p = "b"+ value + " " + code
					write_file.append(p)
				else:
				'''
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
				if index>=0 and data[code]['tv'][index][0]==time:
					data[code]['tv'][index][1] = value
				else:
					data[code]['tv'].append([time,value])
					data[code]['index'] += 1
					index = data[code]['index']

		elif line.startswith("$end"):
			write_file.append(line)
			if checkVars:			# initialize done
				checkVars = False
				startWrite = True

		else:						# sth else
			s = "\t%s"%line
			write_file.append(s)
	#####################################################################

	# WRITE FILE
	if startWrite:
		write_file.append("#1")
		t = 0
		clk = ""
		if int(threshold)>0:
			thr = open(nameGroup[0]+'_threshold.txt','w')
		for code in data:
			if code in safeList:
				t = (int(end_time))/2 + 1
				clk = code
				s = "0%s"%clk
				write_file.append(s)
			else:
				if 'count' in data[code]:
					ltv = len(data[code]['tv'])
					for i in xrange(ltv):			# counter
						if int(data[code]['tv'][i][0])>=int(start_time)  and i>=1:
							a = data[code]['tv'][i][1]
							b = data[code]['tv'][i-1][1]
							if str(a)!="x" and str(b)!="x":
								c = toggle_count(str(a),str(b))
								data[code]['count'] += c
								if int(data[code]['tv'][i][0])>=int(end_time):
									break
					binCount = count_length((data[code]['count']))
					s = "b%s %s"%(binCount, code)
					searchS = searchstring
					if searchS != '':
						tempGroup = searchS.split('/')
						if len(tempGroup)==1:
							for each in data[code]['nets']:
								eachName = each['shortName']
								eachFullName = each['FullName']
								if eachName.startswith(searchS) and int(data[code]['count'])>=int(threshold):
									print "%s\nCount: %s"%(eachFullName, data[code]['count'])
						else:
							for each in data[code]['nets']:
								eachFullName = each['FullName']
								if searchS in eachFullName and int(data[code]['count'])>=int(threshold):
									print "%s\nCount: %s"%(eachFullName, data[code]['count'])
						ifWrite = False
					elif int(data[code]['count'])>=int(threshold):
						if int(threshold)>0:
							for each in data[code]['nets']:
								s = "%s\nCount: %s\n"%(each['FullName'], data[code]['count'])
								thr.write("%s\n"%(s))

					write_file.append(s)
		if int(threshold)>0:
			thr.close()

		s = "#%s"%str(t)
		write_file.append(s)
		for code in safeList:
			s = "1%s"%code
			write_file.append(s)
		end_time = int(end_time) + 1
		write_file.append("#%s"%end_time)
		###########################################################

		if doDiff is True:
			return data, write_file
		
		# SIGNALS RENAMING IN THE WRITTEN FILE
		i = 0
		checkVars = False
		while(i<len(write_file)):
			statement = write_file[i]
			if statement.startswith('$var'):
				l = statement.split()
				code = l[3]
				#size = getActSize(l[2])
				size = int(l[2])
				size = 2**size-1
				count = int(data[code]['count'])
				if int(count)>int(size):
					R = ''.join(l[5:-1])
					if l[5] != '$end':
						'''
						R = ''.join(l[5:-1])
						L = re_len.match(R)
						if L is None:		# 2d array format (hasn't passed test)
							print "############\nERROR LINE: %s\n############\n"%write_file[i]
							print "************\nERROR SECTION: %s\n************\n"%R
							newL = re_len.match(l[6])
							if newL is not None:
								a = newL.group()
								a = a.replace('[','')
								a = a.replace(']','')
								b = a.split(':')
								startBit = b[1]
								endBit = b[0]
							else:
								tempSize = l[2]
								startBit = 0
								endBit = str(int(tempSize)-1)
						else:		
						'''
						L = re_len.match(R)
						if L.group(2) is not None:
							a = L.group(2)
						else:
							a = L.group(1)
						a = a.replace('[','')
						a = a.replace(']','')
						b = a.split(':')
						startBit = b[1]
						endBit = b[0]
					else:
						startBit = '0'
						endBit = '1'

					if int(size)>2 or startBit is not'0' :
						newCode = getNewCode(**data)
						data[newCode] = {'count':0, 'size':0}
						newType = l[1]
						newSize = l[2]
						if L is not None and L.group(2) is not None and L.group(1) is not None:
							write_file[i] = '$var %s\t  %s %s %s %s[%s:%s]  $end'%(l[1],l[2],newCode,l[4],L.group(1),endBit,startBit)
							newName = l[4] + '_%s__%s '%(endBit,startBit) + L.group(1) + '[31:0]'
						else:
							write_file[i] = '$var %s\t  %s %s %s [%s:%s]  $end'%(l[1],l[2],newCode,l[4],endBit,startBit)
					
							newName = l[4] + '_%s__%s'%(endBit, startBit) + ' [31:0]'
						string = '$var %s\t  32 %s %s  $end'%(newType, code, newName)
						for j in data[code]['nets']:				# update N bits data structure
							if j['shortName']==l[4]:
								j['size'] = 32
								j['name'] = newName
								j['shortName'] = l[4] + '_%s__%s'%(endBit, startBit)
								j['length'] = '[31:0]'
								j['FullName'] = j['hier']+j['shortName']+j['length']
								break
						write_file.insert(i+1,string)
						i = i + 1
					elif int(size)<=2:
						newName = ' '.join([l[4],'[31:0]'])
						#newName = l[4] + ' [31:0]'
						write_file[i] = '$var %s\t  32 %s %s  $end'%(l[1],code,newName)
						for j in data[code]['nets']:				# update 1 bit data structure
							if j['shortName']==l[4]:
								j['size'] = 32
								j['length'] = '[31:0]'
								j['FullName'] = j['hier']+j['shortName']+j['length']
								break
			elif '$dumpvars' in statement:
				checkVars = True		# begin initialize
			elif statement.startswith(('x','X','0','1','z','Z')):
				if checkVars is True:
					rep = re_1b_val.match(statement)
					copyCode = rep.group(2)
					copyVal = rep.group(1)
					if int(data[copyCode]['nets'][0]['size'])>1:	# convert 1bit to 32bits init
						write_file[i] = 'b%s %s'%(copyVal, copyCode)

			elif '$end' in statement:
				if checkVars is True:	# initialize done
					checkVars = False
			i = i + 1
		###########################################################################################

		# GENERATE RC FILE
		rc = genRCFile(data, mod, ex)
		s = '.'.join(nameGroup[:-1]) + '_toggle.rc'
		genRc = open(s,'w')
		genRc.write("zoom 0.000000 %s\n"%end_time)
		genRc.write("cursor %s\n\n"%(int(end_time)/2+1))
		for each in rc:
			genRc.write("%s\n"%each)
		genRc.close()
		##################################################

	fh.close()
	return data, write_file, ifWrite

'''
Generate the rc file for all signals
'''
def genRCFile(data, mod, ex):
	sortDict = {}
	rc = []

	for each in data:
		if mod is not '':
			if 'nets' in data[each]:
				i = 0
				while i<len(data[each]['nets']):
					if 'hier' in data[each]['nets'][i]:
						if ex is True:
							if mod == data[each]['nets'][i]['hier']:
								if 'count' in data[each]:
									sortDict[each] = data[each]['count']
								else:
									sortDict[each] = 0
						else:			
							if mod in data[each]['nets'][i]['hier']:
								if 'count'  in data[each]:
									sortDict[each] = data[each]['count']
								else:
									sortDict[each] = 0
					i += 1
		elif mod is '':
			if 'count' in data[each]:
				sortDict[each] = data[each]['count']
			else:
				sortDict[each] = 0

	ot = sorted(sortDict.items(), key=lambda (k,v): v, reverse = True)
	for each in ot:
		co = each[0]

		if 'nets' in data[co]:
			size = data[co]['nets'][0]['length']
			i = 0
			while i < len(data[co]['nets']):
				h = data[co]['nets'][i]['hier']
				n = data[co]['nets'][i]['name_2']
				if size!='1':
					st = "addSignal -h 15 -UNSIGNED -HEX  %s"%('/'.join([h,n]))
				else:
					st = "addSignal -h 15 %s"%('/'.join([h,n]))
				rc.append(st)
				i+=1
	return rc

'''
According to the option -d
	First, parsing two vcd file separately and get each data structure
	Then, compare the signals with two data structure
	Finally, output the text file that containing the info of signals.
'''
def compare(v1, v2, t1, t2, mod, ex, threshold, searchstring):
	wf = []
	d1 = {}
	d2 = {}
	both = []
	doDiff = True
	
	data_v1, write_v1 = parse_vcd(v1,t1,t2,doDiff,'',False, threshold, searchstring)
	data_v2, write_v2 = parse_vcd(v2,t1,t2,doDiff,'',False, threshold, searchstring)

	newGroup = v1.split('.')
	fp = open(newGroup[0]+'_toggle.vcd', 'w')
	for each in write_v1:
		fp.write("%s\n"%each)
	fp.close()
	newGroup = v2.split('.')
	fp = open(newGroup[0]+'_toggle.vcd', 'w')
	for each in write_v2:
		fp.write("%s\n"%each)
	fp.close()

	st = []
	for code in data_v1:
		if 'count' in data_v1[code]:
			to1 = data_v1[code]['count']
			if 'name' in data_v1[code]['nets'][0]:
				n1 = data_v1[code]['nets'][0]['FullName']
				d1[n1] = to1
	for corresp in data_v2:
		if 'count'in data_v2[corresp]:
			to2 = data_v2[corresp]['count']
			if 'name' in data_v2[corresp]['nets'][0]:
				n2 = data_v2[corresp]['nets'][0]['FullName']
				d2[n2] = to2

	for i in d1:
		if mod in i:
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
		if mod in j:
			if j not in d1:
				first = '-'
				second = d2[j]
				difference = second
				if difference != 0:
					st = ['%s:\n'%j,'%s: %s\n'%(v1,first),'%s: %s\n'%(v2,second),'Difference: +', '%s'%difference]
					both.append(st)
	wf = sorted(both, key=  lambda x: int(x[4]),reverse=True)
	return wf

'''
Main function
	for command line option
'''
def main():
	t = time.clock()

	msg = "myParser.py [-h] [-d vcd_file_1 vcd_file_2]\n\t\t\t|[vcd_file] \n\t\t\t--time (start_time) (end_time) \n\t\t\t[--module (module_name)] [--exclude] \n\t\t\t[--boundary] \n\t\t\t[--start] \n\t\t\t[--fit]"
	parser = argparse.ArgumentParser(description='myVCDParser Script ver_0.1', usage=msg)
	parser.add_argument('vcd', nargs='?', action='store', help='The vcd file you want to parse.')
	parser.add_argument('-d', nargs=2, action='store', dest='comp_file', help='Compare two vcd files. NOTE: rc file will not be generated.', metavar=('vcdfile_1','vcd_file_2'))
	parser.add_argument('-t', nargs=2, action='store', dest='t', help='The start time and the end time. (unit: ns)', required=True, metavar=('start_time','end_time'))
	parser.add_argument('-m', nargs='?', action='store', dest='mod', help='Show all signals under this hierarchy including all hierarchy.', metavar=('module'))
	parser.add_argument('-e', action='store_true',  help='Show all signals under only this hierarchy. Use with -module')
	parser.add_argument('-b', nargs='?', action='store', dest='min', help='Show only the signals larger than this value. NOTE: A txt file will be generated.', metavar=('threshold'))
	parser.add_argument('-s', nargs='?', action='store', dest='searchstring', help='Show only the name of signals begin with string you input. NOTE: vcd file and rc file will not be generated.', metavar=('string'))


	args = parser.parse_args()

	if args.vcd is None and args.comp_file is None and args.t is not None:
		print parser.print_help()
		parser.error("You must choose one vcd file or two vcd files.")
		return 
	if args.mod is not None:
		module = args.mod
		if args.e is not None:
			exclude = args.e
	elif args.mod is None:
		module = ''
		if args.e is None :
			parser.error("--exclude can't be used without --module")
			return
		exclude = False
	
	if args.searchstring!=None:
		searchstring = args.searchstring
		tempGroup = searchstring.split('/')
		for tempString in tempGroup:
			s = re.match("^[a-zA-Z0-9_]*$",tempString)
			if s is None:
				parser.error("The string must be composed of letters and numbers and underscore")
				return 
		if searchstring.endswith('/'):
			parser.error("The end of string can't be slash.")
			return 
	else:
		searchstring = ''
	if args.min != None:
		threshold = args.min
	else:
		threshold = 0
	if args.vcd!=None:
		vcd_file, start_time, end_time = args.vcd, args.t[0], args.t[1]

		if float(start_time)<0 or float(end_time)<0:
			print parser.print_help()
			parser.error("Time must be positive or zero.")
			return 
		elif float(end_time)<float(start_time):
			print parser.print_help()
			parser.error("start_time must be smaller than end_time.")
			return 
		vcdGroup = vcd_file.split('.')
		if (vcdGroup is not None and vcdGroup[len(vcdGroup)-1] != "vcd") or (vcdGroup is None):
			parser.error("Only support vcd file input.")
			return
		
		vcd, genWrite, ifWrite = parse_vcd(vcd_file, start_time, end_time, False, module, exclude, threshold, searchstring)		# vcd = record all time's signals
		if ifWrite:
			nameGroup = vcd_file.split('.')
			newName = '.'.join(nameGroup[:-1]) + '_toggle'
			genf = open(newName+'.vcd','w')
			for each in genWrite:
				genf.write("%s\n"%each)
			genf.close()

		
	elif args.comp_file!=None:
		vcd_file_1, vcd_file_2 = args.comp_file[0], args.comp_file[1]
		start_time, end_time = args.t[0], args.t[1]
		if float(start_time)<0 or float(end_time)<0:
			print parser.print_help()
			parser.error("Time must be positive or zero.")
			return 
		elif float(end_time)<float(start_time):
			print parser.print_help()
			parser.error("start_time must be smaller than end_time.")
			return 
		compWrite = compare(vcd_file_1, vcd_file_2, start_time, end_time, module, exclude, threshold, searchstring)
		compf = open('diff.txt','w')
		compf.write("Difference between %s and %s, Time: %sns ~ %sns\n"%(vcd_file_1, vcd_file_2, start_time, end_time))
		for i in compWrite:
			for j in i:
				compf.write("%s"%j)
			compf.write("\n\n")

	return 

if __name__ == "__main__":
	main()
