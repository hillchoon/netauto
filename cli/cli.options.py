#!/usr/bin/python3

import sys, getopt

def main(argv):
   host_list = ''
   outputfile = ''
   try:
      args, opts = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
      print (args)
      print (opts)
   except getopt.GetoptError:
      print ('cli.options.py -i <inputfile> -o <outputfile>')
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print ('usage: cli.options.py -i <inputfile> -o <outputfile>')
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-o", "--ofile"):
         outputfile = arg
   print ('Input file is "', inputfile)
   print ('Output file is "', outputfile)

if __name__ == "__main__":
   main(sys.argv[1:])