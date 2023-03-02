import sys
import argparse

parser = argparse.ArgumentParser(prog = 'floor.obj.gen.py', description = 'Generate Floor Objects in Bulk on PM')
parser.add_argument('-x', '--switch', type=str, help='function switch: "icon" for floor objects, "fixed" for fixed cables, "patching" for patching in comm rooms')
parser.add_argument('-s', '--source_file', type=str, help='directory of source file')
parser.add_argument('-o', '--output_file', type=str, help='directory of output file')
parser.add_argument('-c', '--campus', type=str, help='campus name')
parser.add_argument('-b', '--building', type=str, help='building name')
parser.add_argument('-f', '--floor', type=str, help='floor name')
parser.add_argument('-cf', '--closet_floor', type=str, help='closet floor')
parser.add_argument('-cst', '--closet', type=str, help='comm room number')
args = parser.parse_args()

# initiate arguments
if args.closet_floor is None:
	args.closet_floor = ''
if args.closet is None:
	args.closet =''

faceplate_template = [
'Face Plate 1 Port Copper',
'Face Plate 2 Port Copper',
'Face Plate 3 Port Copper',
'Face Plate 4 Port Copper',
'Face Plate 5 Port Copper',
'Face Plate 6 Port Copper',
'Face Plate 7 Port Copper',
'Face Plate 8 Port Copper',
'Face Plate 9 Port Copper',
'Face Plate 10 Port Copper'
]

if args.switch == 'icon':
	run_number = 0
	f_o = open(f'{args.output_file}', 'a')
	f_o.write('Equipment Location,Equipment Label,Equipment Template' + '\n')
	with open(f'{args.source_file}') as f_source:
		circuits = f_source.readlines()
#		print (len(circuits))
		for i in range(len(circuits)-1):
			circuit_id = circuits[i].strip()
			next_circuit_id = circuits[i+1].strip()
#			print ('i=' + str(i) + ', id:' + circuit_id + ', next id: '+next_circuit_id)
			if circuit_id[:len(circuit_id)-1] == next_circuit_id[:len(next_circuit_id)-1]:
	#			print ('id:' + circuit_id + ', next id: ' + next_circuit_id)
				same_set_run = True
				run_number+=1
	#			print (run_number)
			else:
				same_set_run = False
				f_o.write('"' + args.campus + ',' + args.building + ',' + args.floor + '",' + 
					circuit_id[:len(circuit_id)-1] + ',' + faceplate_template[run_number] + '\n')
				run_number = 0
	f_source.closed
	f_o.close()
# note: when processing icons for ap circuits:
# 1. if an ap set-run has only 1 circit, script creates a 1-port faceplate ided as circuit id without the last digit;
# 2. if an ap set-run has 2 circuits, script creats a 2-port faceplate ided as same as 1;
# 3. if multiple ap set-runs to same room have circuit ids like xxxx-ap1/2/.../n (n<=10), script creates a n-port faceplate ided as same as 1

elif args.switch == 'fixed':
	f_o = open(f'{args.output_file}','a')
	f_o.write('Cable Label,Cable Template,Equipment,Port,Connector,Equipment,Port,Connector \n')
	with open(f'{args.source_file}') as f_source:
		fixed_cables = f_source.readlines()
		for single_cable in fixed_cables:
			single_cable = single_cable.split()
#			print (single_cable)
			f_o.write(',Fixed Copper,"' + args.campus + ',' + args.building + ',' + args.floor + ',' + 
				single_cable[0] + '",' + single_cable[1] + '[Rear],Copper Punch Down,"' + args.campus + ',' + 
				args.building + ',' + args.closet_floor + ',' + args.closet + ',RK' + single_cable[2] + ',PP' + 
				single_cable[3] + '",' + single_cable[4] + '[Rear],Copper Punch Down \n')
	f_source.closed
	f_o.close()
else:
	pass