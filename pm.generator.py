import argparse


def parse_args():
    parser = argparse.ArgumentParser(description='Generate PM update file')
    parser.add_argument('-x', '--switch', choices=["icon", "fixed", "patch"], 
        help='function switch: "icon" for floor objects, "fixed" for fixed cables, "patch" for patching in comm rooms')
    parser.add_argument('-s', '--source_file', metavar='FILE', help='directory of source file')
    parser.add_argument('-o', '--output_file', metavar='FILE', help='directory of output file')
    parser.add_argument('-c', '--campus', choices=["Burnaby", "Surrey", "Vancouver"], help='campus name')
    parser.add_argument('-b', '--building', type=str, help='building name')
    parser.add_argument('-f', '--floor', type=str, help='floor name')
    parser.add_argument('-cf', '--closet_floor', type=str, help='floor of closet')
    parser.add_argument('-cst', '--closet', type=str, help='comm room number')
    parser.add_argument('-rk', '--rack', type=str, help='switch rack number')
    return parser.parse_args()


def process_icon(args):
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

    with open(args.source_file) as f_source, open(args.output_file, 'a') as f_o:
        f_o.write('Equipment Location,Equipment Label,Equipment Template\n')
        circuits = [line.strip() for line in f_source.readlines()]
        run_number = 0
        for i in range(len(circuits)-1):
            circuit_id = circuits[i].strip()
            next_circuit_id = circuits[i+1].strip()
            if circuit_id[:len(circuit_id)-1] == next_circuit_id[:len(next_circuit_id)-1]:
                same_set_run = True
                run_number += 1
            else:
                same_set_run = False
                f_o.write(f'"{args.campus},{args.building},{args.floor}",{circuit_id[:len(circuit_id)-1]},{faceplate_template[run_number]}\n')
                run_number = 0


def process_fixed(args):
    with open(args.source_file) as f_source, open(args.output_file, 'a') as f_o:
        f_o.write('Cable Label,Cable Template,Equipment,Port,Connector,Equipment,Port,Connector\n')
        fixed_cables = [line.strip() for line in f_source.readlines()]
        for single_cable in fixed_cables:
            single_cable = single_cable.split()
            f_o.write(f',Fixed Copper,"{args.campus},{args.building},{args.floor},{single_cable[0]}",{single_cable[1]}[Rear],Copper Punch Down,"{args.campus},{args.building},{args.closet_floor},{args.closet},RK{single_cable[2]},PP{single_cable[3]}",{single_cable[4]}[Rear],Copper Punch Down\n')


def process_patch(args):
    with open(args.source_file) as f_source, open(args.output_file, 'a') as f_o:
        f_o.write('Cable Label,Cable Template,Equipment,Port,Connector,Equipment,Port,Connector\n')
        patches = [line.strip() for line in f_source.readlines()]
        for patch in patches:
            patch = patch.split()
            f_o.write(f',Patch Cord RJ45,"{args.campus},{args.building},{args.floor},{args.closet},{args.rack},{patch[0]} {patch[1]}",{patch[2]}[Front],RJ45 Active,"{args.campus},{args.building},{args.closet_floor},{args.closet},RK{patch[3]},PP{patch[4]}",{patch[5]}[Front],RJ45\n')

def main():
    args = parse_args()
    if args.switch == 'icon':
        process_icon(args)
    elif args.switch == 'fixed':
        process_fixed(args)
    elif args.switch == 'patch':
        process_patch(args)
    else:
        pass


if __name__ == "__main__":
    main()