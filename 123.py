#!/usr/bin python

import sys, re

def count_length(l):
	return str(bin(l)[2:])
def toggle_count(a, b):
	extend = 0
	if len(a)!=len(b):
		if len(a)>len(b):
			extend = len(a)-len(b)
			b = '0'*extend + b
		else:
			extend = len(b)-len(a)
			a = '0'*extend + a
	print "a:%s\nb:%s"%(a,b)
	#c = int(a)^int(b)
	Sum = 0
	for x,y in zip(a,b):
		s = int(x)^int(y)
		if s==1:
			Sum+=1

	return Sum
def parse_vcd(vcd_file, start_time, end_time):
	re_time = re.compile(r"^#(\d+)")				# re obj of '#(time)'
	re_1b_val = re.compile(r"^([01zxZX])(.+)")		# re obj of e.g '0%'
	re_Nb_val = re.compile(r"^[b|r](\S+)\s+(.+)")	# re obj of e.g 'b0 @', 'b111 #'
	re_info = re.compile(r"^(\s+\S+)+")			# re obj of e.g '	Jun, ...'
	re_t_val = re.compile(r"^(\d+)\s+(.+)")

	data = {}		# var structure values
	hier = []		# scope hierachy
	time = 0		# each '#(time)'
	before = 0
	index = -1
	write_file = [] # write file list
	checkVars = False
	startWrite = False
	safeList = []

	fh = open(vcd_file, 'r')
	print "Open File!"
	print "Start: %s, End: %s"%(start_time, end_time)

	while True:
		line = fh.readline()
		if line =='':		# EOF
			break
		line = line.strip()

		if "$date" in line:
			write_file.append(line)
		elif "$timescale" in line:
			write_file.append(line)
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
			vPath = '.'.join(hier)
			vFullName = vPath + vName
			if vCode not in data:
				data[vCode] = {}
				if 'nets' not in data[vCode]:
					data[vCode]['nets'] = []
				var_struct = {
					'type': vType,
					'name': vName,
					'size': vSize,
					'hier': vPath,
				}
				if var_struct not in data[vCode]['nets']:
					data[vCode]['nets'].append(var_struct)
			if 'clk' in str(vName):
				temp = "$var %s\t  %s %s\t%s  $end"%(vType, vSize, vCode, vName)
				safeList.append(vCode)
			else:	
				temp = "$var %s\t  %s %s\t%s  $end"%(vType, vSize, vCode, str(vName))
			write_file.append(temp)
		elif line.startswith('#'):
			re_time_match = re_time.match(line)
			time = re_time_match.group(1)		# recording #(time)
			if (int(time)>int(end_time)):
				break
			if time=='0':
				write_file.append(line)
		elif line.startswith(('0', '1', 'x', 'z', 'b', 'r','X', 'Z')):
			if line.startswith(('0', '1', 'x', 'z', 'X', 'Z')):
				t = re_t_val.match(line)
				if t:
					s = "\t%s"%t.group()
					write_file.append(s)
					continue
				else:
					m = re_1b_val.match(line)
			elif line.startswith(('b', 'r')):
				m = re_Nb_val.match(line)
			value = m.group(1)
			code = m.group(2)
			
			if checkVars:
				write_file.append(line)
			if (code in data):
				if 'tv' not in data[code]:
					data[code]['tv'] = []
				if 'index' not in data[code]:
					data[code]['index'] = -1
				if 'count' not in data[code]:
					data[code]['count'] = 0

				data[code]['tv'].append([time, value])
				data[code]['index'] += 1
				index = data[code]['index']
				if int(time)>=int(start_time) and index>=1:
					print "time:%s, sT:%s"%(time, start_time)
					a = data[code]['tv'][index][1]
					b = data[code]['tv'][index-1][1]
					c = toggle_count(str(a),str(b))
					if code==')':
						print "):%s"%c
					data[code]['count'] += c
				
		elif line.startswith("$end"):
			write_file.append(line)
			if checkVars:
				checkVars = False
				startWrite = True
		else:
			s = "\t%s"%line
			write_file.append(s)
	if startWrite:
		write_file.append("#%s"%start_time)
		t = 0
		clk = ""
		for code in data:
			print "Code:%s\n%s\n"%(code,data[code])
			if code in safeList:
				t = (int(end_time)-int(start_time)+1)/2 + int(start_time)
				clk = code
				s = "0%s"%clk
				write_file.append(s)
			else:
				if 'count' in data[code]:
					binCount = count_length(data[code]['count'])
					s = "b%s %s"%(binCount, code)
					write_file.append(s)
		s = "#%s"%str(t)
		write_file.append(s)
		for code in safeList:
			s = "1%s"%code
			write_file.append(s)
			
		end_time = int(end_time) +1
		write_file.append("#%s"%end_time)

	fh.close()
	return data, write_file

def main():
	vcd_file, start_time, end_time = sys.argv[1], sys.argv[2], sys.argv[3]

	vcd, write_file = parse_vcd(vcd_file, start_time, end_time)		# vcd = record all time's signals
	for p in write_file:
		print p
	f = open('t1.vcd','w')

	for each in write_file:
		f.write("%s\n"%each)

if __name__ == "__main__":
	main()
