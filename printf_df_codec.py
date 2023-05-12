#! python
#
# This is a codec to decode printf-encoded data.
#
# To be used in conjunction with a system that utilizes by the printf-encoded library:
# 	https://github.com/ManuelonGithub/sprintf_encoding
#
# MIT License
#
# Copyright (c) 2023 ManuelonGithub
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import struct
import codecs

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

# usage:
# import printf_df_codec
# codecs.register(lambda c: printf_df_codec.getregentry() if c == 'printf_df' else None)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
""" Helper data structures and functions """

VALUE_FORMAT = {
	'd':   '<i', 'u':   '<I', 'o':   '<I', 'x':   '<I', 'X':   '<I',
	'hd':  '<h', 'hu':  '<H', 'ho':  '<H', 'hx':  '<H', 'hX':  '<H',
	'hhd': '<b', 'hhu': '<B', 'hho': '<B', 'hhx': '<B', 'hhX': '<B',
}

SPECIAL_CHARS = {
	'\xD8': 'X',
	'\xE4': 'd',
	'\xE9': 'i',
	'\xEF': 'o',
	'\xF5': 'u',
	'\xF8': 'x',
}

NON_VALUE_CHARS     = set('cs%\0')
FLOAT_VAL_CHARS     = set('eEfFgG')

SPECIFIER_CHARS     = (
	set(SPECIAL_CHARS.values()) | 
	set(SPECIAL_CHARS.keys()) | 
	NON_VALUE_CHARS | 
	FLOAT_VAL_CHARS
)

def sprintf(print_fmt: str, val: any) -> str:
	try:
		return (print_fmt % val)
	except TypeError:
		return print_fmt

def parse_length_chars(print_fmt: str, val_char: str = None) -> tuple[str, str]:
	# python printf does not like length characters that aren't h,l, and L
	# we're supporting C99 printf form so a format that uses hh,ll,j,z,t should still be processed 
	# lengths >4 bytes are not supported though - it's all parsed as 4 bytes
	# this function is meant to detect those length characters and remove them from the format
	# It will also return a length string that contains an h or hh if found in the format,
	# since that info correlates to how many bytes in the raw data pertain to the print value
	len_char_set = set('hlLjzt')
	len_chars = ''
	if (print_fmt[-1] in len_char_set):
		c = print_fmt[-1]
		print_fmt = print_fmt[:-1]
		if c == 'h':
			len_chars = c
			if print_fmt[-1] == 'h':
				len_chars = c + print_fmt[-1]
				print_fmt = print_fmt[:-1]
		if c == 'l' and print_fmt[-1] == 'l':
			print_fmt = print_fmt[:-1]

	if (val_char):
		return print_fmt + val_char, len_chars + val_char
	else:
		return print_fmt, len_chars

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def printf_encode(data: str, errors='strict') -> tuple[str, int]:
	# do nothing - no printf from the writer direction :)
	return (bytes(data, 'ascii', errors), len(data))

def printf_decode(data, errors='strict') -> tuple[str, int]:
	if (type(data) == memoryview):
		data_split = data.tobytes().split(b'\xA5', 1)
	else:
		data_split = data.split(b'\xA5', 1)

	r = data_split[0].decode('ascii', errors)

	while (len(data_split) > 1):
		print_data = data_split[1]

		i = 0
		print_fmt = '%'
		val_fmt = ''

		while (i < len(print_data)):
			c = chr(print_data[i])

			if c == '*':
				i = i + 1
				print_fmt = print_fmt + str(print_data[i])
			elif c != '\0':
				print_fmt = print_fmt + chr(print_data[i])
			i = i + 1

			if (c in SPECIFIER_CHARS):
				break

		if (c in VALUE_FORMAT):
			print_fmt, val_fmt = parse_length_chars(print_fmt[:-1], c)
			val_fmt = VALUE_FORMAT[val_fmt]
			val_len = struct.calcsize(val_fmt)
			r = r + sprintf(print_fmt, struct.unpack(val_fmt, print_data[i:i+val_len])[0])
			i = i + val_len

		elif (c in SPECIAL_CHARS):
			print_fmt = parse_length_chars(print_fmt[:-1], SPECIAL_CHARS[c])[0]
			r = r + sprintf(print_fmt, print_data[i])
			i = i + 1

		elif (c in FLOAT_VAL_CHARS):
			r = r + sprintf(print_fmt, struct.unpack('<f', print_data[i:i+4])[0])
			i = i + 4
		
		else:
			if (c == '%'):
				r = r + '%'
			elif (c == 'c'):
				r = r + sprintf(print_fmt, print_data[i])
				i = i + 1

			elif (c == 's'):
				end = print_data[i:].find(b'\0')
				s = print_data[i:i+end].decode('ascii', errors)
				i = i + end + 1
				r = r + sprintf(print_fmt, s)
			else:	# null-terminator case or end-of-bytes case
				if (print_fmt[-1] == '\0'):
					print_fmt = print_fmt[:-1]
				r = r + print_fmt
		
		data_split = print_data[i:].split(b'\xA5', 1)
		r = r + data_split[0].decode('ascii', errors)

	return (r, len(r))

class Printf_Codec(codecs.Codec):
    def encode(self, data: str, errors='strict') -> bytes:
        return bytes(data, 'ascii', errors)

    def decode(self, data: bytes, errors='strict') -> str:
        return printf_decode(data, errors)[0]

class Printf_IncrementalEncoder(codecs.IncrementalEncoder):
		def encode(self, input: str, final: bool = False) -> bytes:
			return bytes(input, 'ascii', self.errors)

class Printf_IncrementalDecoder(codecs.IncrementalDecoder):
	FIND_FMT_START = 0
	FIND_FMT_END = 1
	CAP_VALUE = 2
	CAP_TEXT = 3
	CAP_WILD = 4

	def __init__(self, errors='strict'):
		self.errors = errors

		self.print_fmt = ''
		self.data_buffer = b''
		self.val_len = 0
		self.val_fmt = ''

		self.state = self.FIND_FMT_START

	def reset(self) -> None:
		self.print_fmt = ''
		self.data_buffer = b''
		self.val_len = 0
		self.val_fmt = ''

		self.state = self.FIND_FMT_START

	def getstate(self) -> tuple[bytes, int]:
		return (self.print_fmt.encode('ascii')+self.data_buffer, self.state)
	
	def setstate(self, state: tuple[bytes, int]) -> None:
		self.reset()
		self.decode(state[0])

	def decode(self, input: bytes, final: bool = False) -> str:
		r = ""
		for val in input:
			c = chr(val)
			if self.state == self.FIND_FMT_START:	# start - look for '\xA5'
				if c == '\xA5':
					self.reset()
					self.print_fmt = '%'
					self.state = self.FIND_FMT_END
				elif (c != '\0'):
					r = r + c

			elif self.state == self.FIND_FMT_END:
				self.print_fmt = self.print_fmt + c

				if c in VALUE_FORMAT:
					self.print_fmt, self.val_fmt = parse_length_chars(self.print_fmt[:-1], c)
					self.val_fmt = VALUE_FORMAT[self.val_fmt]
					self.val_len = struct.calcsize(self.val_fmt)
					self.state = self.CAP_VALUE

				elif c in SPECIAL_CHARS:
					self.print_fmt = parse_length_chars(self.print_fmt[:-1], SPECIAL_CHARS[c])[0]
					self.val_fmt = '<B'
					self.val_len = 1
					self.state = self.CAP_VALUE
				
				elif c in FLOAT_VAL_CHARS:
					self.val_fmt = '<f'
					self.val_len = 4
					self.state = self.CAP_VALUE

				elif c in NON_VALUE_CHARS:
					if c == 'c':
						self.val_fmt = '<B'
						self.len = 1
						self.state = self.CAP_VALUE			
					elif c == 's':
						self.state = self.CAP_TEXT
					elif c == '%':
						r = r + '%'
						self.FIND_FMT_START
					else:
						r = r + self.print_fmt
						self.FIND_FMT_START
				
				elif c == '*':
					self.print_fmt = self.print_fmt[0:-1]
					self.state = self.CAP_WILD

			elif self.state == self.CAP_VALUE:
				self.data_buffer = self.data_buffer + val.to_bytes(1, 'little')
				if len(self.data_buffer) == self.val_len:
					self.state = self.FIND_FMT_START
					r = r + sprintf(self.print_fmt, struct.unpack(self.val_fmt, self.data_buffer)[0])

			elif self.state == self.CAP_TEXT:
				if val == 0:
					r = r + sprintf(self.print_fmt, self.data_buffer.decode('ascii', self.errors))
					self.state = self.FIND_FMT_START
				else:
					self.data_buffer = self.data_buffer + val.to_bytes(1, 'little')

			elif self.state == self.CAP_WILD:
				self.print_fmt = self.print_fmt + str(val)
				self.state = self.FIND_FMT_END

		if (final and self.state != self.FIND_FMT_START):
			r = r + self.print_fmt + self.data_buffer.decode('ascii', self.errors)
			self.reset()

		return r
		
class Printf_StreamWriter(Printf_Codec, codecs.StreamWriter):
    """Combination of Printf codec and StreamWriter"""

class Printf_StreamReader(Printf_Codec, codecs.StreamReader):
    """Combination of Printf codec and StreamReader"""

def getregentry():
    """encodings module API"""
    return codecs.CodecInfo(
        name='printf_df',
        encode=printf_encode,
        decode=printf_decode,
        incrementalencoder=Printf_IncrementalEncoder,
        incrementaldecoder=Printf_IncrementalDecoder,
        streamwriter=Printf_StreamWriter,
        streamreader=Printf_StreamReader,
    )




if __name__ == "__main__":
	codecs.register(lambda c: getregentry() if c == 'printf_df' else None)

	print(bytes.decode(b'The value is \xA5010.4f\x00\x00\x90\xbf.\n', 'printf_df'))
	print(bytes.decode(b'The value is \xA50*\x0A.*\x04f\x00\x00\x90\xbf.\n', 'printf_df'))
	print(bytes.decode(b'The value is \xA5+20X\xef\xbe\xad\xde.\n', 'printf_df'))
	print(bytes.decode(b'The value is \xA5%\xA5uc\x00\x00\x00.\n', 'printf_df'))
	print(bytes.decode(b'The data is \"\xA5-11shello\x00\".\n', 'printf_df'))
	print(bytes.decode(b'The data is \"\xA5-11.5shello there\x00\".\n', 'printf_df'))
	print(bytes.decode(b'The value is \xA5#+- 010uc\x00\x00\x00.\n', 'printf_df'))
	print(bytes.decode(b'The value is \xA5lu\x63\x00\x00\x00 and the data is \"\xA5s\x68\x65\x6C\x6C\x6F\x00\".\n', 'printf_df'))

	print(bytes.decode(b'The value is \xA5ll\xF5\x63 and the data is \"\xA5s\x68\x65\x6C\x6C\x6F\x00\".\n', 'printf_df'))
	print(bytes.decode(b'The value is \xA5hh\xF8\x12\xA5hh\xF8\x34\xA5hh\xF8\x56\xA5hh\xF8\x78\n', 'printf_df'))
	
	print(bytes.decode(b'The value is \xA5hhd\xff', 'printf_df'))
	print(bytes.decode(b'The value is \xA5123456\0 and the other value is \xA5\xEF@', 'printf_df'))
