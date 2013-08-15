#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Test raw data with MSSImage class.

import sys
from mss import MSSImage


if len(sys.argv) < 4:
	print('python {0} data.raw width height'.format(sys.argv[0]))
else:
	with open(sys.argv[1], 'rb') as f:
		data = f.read()
		width = sys.argv[2]
		height = sys.argv[3]
	try:
		mss = MSSImage(data, width, height)
		mss.dump(output=sys.argv[1])
	except Exception as ex:
		print(ex)
		raise
