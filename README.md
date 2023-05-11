# printf_decoding_py_codec

Python codec class that will decode printf encoded data.

It was inspired by the [hexlify codec](https://github.com/pyserial/pyserial/blob/master/serial/tools/hexlify_codec.py) found in the python serial mopdule.

It implements all functions required by the [python codec class](https://docs.python.org/3/library/codecs.html), but the encoding side simply turns a python string into a byte array.

MIT License, 
Copyright (c) 2023 ManuelonGithub
## Usage

To use the decoder in your project you will need to add the following lines into your python script:

```
import printf_df_codec
codecs.register(lambda c: printf_df_codec.getregentry() if c == 'printf_df' else None)
```

Then you can perform decoding on an complete printf encoded bytearray and retreive the formatted string with the following snippet:

```bytes.decode(b'The value is \xA5010.4f\x00\x00\x90\xbf.\n', 'printf_df'))```

or

```b'The value is \xA5010.4f\x00\x00\x90\xbf.\n'.decode('printf_df')```
