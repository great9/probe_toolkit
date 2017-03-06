def uchar_to_bits(uchar):
	if isinstance(uchar, int):
		bits = bin(uchar)[2:]
	elif len(uchar)==1:
		bits = bin(ord(uchar))[2:] 	# cause the first two are 0b
	for x in range(len(bits),8):		# 1 uchar should return 8 bits
		bits = '0{}'.format(bits)
	return bits

def reverse_bits(bits):
	out = ''
	length = len(bits) -1
	for x in range(0,length+1):
		out += bits[(length-x)]
	return out

def char_to_hex(char):
	buf = ''
	for x in char:
		buf += hex(ord(x))[2:].rjust(2,'0')
	return buf

def uchar_tuple_to_bits(utuple):
	if isinstance(utuple, tuple):
		buf = ''
		for uc in utuple:
			uc = uchar_to_bits(uc)
			if uc != None:
				buf = uc + buf
		return buf
