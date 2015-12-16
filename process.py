# This code is horrible. Apologies to anyone who reads it. I was feeling lazy. If chanted out loud, it may or may not awaken Cthulu.
# Basically, reads in from stdin some HTML with Fortran in <pre><code>-blocks, semantically colors it, and outputs the modified HTML on stdout.

from __future__ import print_function # Make it compatible with Python2.6+
import sys
import re # Yes, this is all based on regular expressions. What could possibly go wrong?
import tempfile
import subprocess
import collections
import itertools

def tag(code):
	"""Add semantic tags to Fortran code. This is all horrible ad-hoc and just barely works, even for a small subset of Fortran. But it's good enough for now. Until it breaks apart horribly."""

	keywords = collections.OrderedDict() # Ensure that things are processed in the right order
	keywords['typename'] = ['integer','logical','real','double precision','character', 'complex']
	keywords['control'] = ['end if','else if','if','then','else','select case','case default','case', 'return', 'enddo', 'endif','goto','cycle','call']
	keywords['attribute'] = ['optional','intent','parameter','allocatable','target','pointer','pure','elemental', 'dimension','external','private','public','protected','save','recursive','result']
	keywords['loop'] = ['do concurrent','do while','do','forall','where','elsewhere', 'end do', 'end where']
	keywords['other'] = ['error stop','extends','block','assign','backspace','data','close','common','continue','data','endfile','entry','equivalence','format','function','implicit','inquire','intrinsic','open','pause','print','program','read','return','rewind','rewrite','stop','subroutine','write','allocate','contains','deallocate','exit','include','interface','module','namelist','nullify','only','operator','procedure','select','sequence','use','abstract','associate','asynchronous','bind','class','deferred','enum','enumerator','final','flush','generic','import','non_overridable','nopass','pass','value','volatile','wait','codimension','contiguous','critical','submodule','sync all','sync images','sync memory','unlock','lock','type','end program','end function', 'end subroutine','end module','end interface','end associate','end block','end type', 'end select']
	keywords['intrinsic'] = ['abort', 'abs', 'access', 'achar', 'acos', 'acosh', 'adjustl', 'adjustr', 'aimag', 'aint', 'alarm', 'all', 'allocated', 'and', 'anint', 'any', 'asin', 'asinh', 'associated', 'atan', 'atan2', 'atanh', 'atomic_define', 'atomic_ref', 'backtrace', 'bessel_j0', 'bessel_j1', 'bessel_jn', 'bessel_y0', 'bessel_y1', 'bessel_yn', 'bge', 'bgt', 'bit_size', 'ble', 'blt', 'btest', 'c_associated', 'c_f_pointer', 'c_f_procpointer', 'c_funloc', 'c_loc', 'c_sizeof', 'ceiling', 'char', 'chdir', 'chmod', 'cmplx', 'co_max', 'co_min', 'co_sum', 'command_argument_count', 'compiler_options', 'compiler_version', 'conjg', 'cos', 'cosh', 'count', 'cpu_time', 'cshift', 'ctime', 'date_and_time', 'dble', 'dcmplx', 'digits', 'dim', 'dot_product', 'dprod', 'dreal', 'dshiftl', 'dshiftr', 'dtime', 'eoshift', 'epsilon', 'erf', 'erfc', 'erfc_scaled', 'etime', 'execute_command_line', 'exit', 'exp', 'exponent', 'extends_type_of', 'fdate', 'fget', 'fgetc', 'floor', 'flush', 'fnum', 'fput', 'fputc', 'fraction', 'free', 'fseek', 'fstat', 'ftell', 'gamma', 'gerror', 'getarg', 'get_command', 'get_command_argument', 'getcwd', 'getenv', 'get_environment_variable', 'getgid', 'getlog', 'getpid', 'getuid', 'gmtime', 'hostnm', 'huge', 'hypot', 'iachar', 'iall', 'iand', 'iany', 'iargc', 'ibclr', 'ibits', 'ibset', 'ichar', 'idate', 'ieor', 'ierrno', 'image_index', 'index', 'int', 'int2', 'int8', 'ior', 'iparity', 'irand', 'is_iostat_end', 'is_iostat_eor', 'isatty', 'ishft', 'ishftc', 'isnan', 'itime', 'kill', 'kind', 'lbound', 'lcobound', 'leadz', 'len', 'len_trim', 'lge', 'lgt', 'link', 'lle', 'llt', 'lnblnk', 'loc', 'log', 'log10', 'log_gamma', 'long', 'lshift', 'lstat', 'ltime', 'malloc', 'maskl', 'maskr', 'matmul', 'max', 'maxexponent', 'maxloc', 'maxval', 'mclock', 'mclock8', 'merge', 'merge_bits', 'min', 'minexponent', 'minloc', 'minval', 'mod', 'modulo', 'move_alloc', 'mvbits', 'nearest', 'new_line', 'nint', 'norm2', 'not', 'null', 'num_images', 'or', 'pack', 'parity', 'perror', 'popcnt', 'poppar', 'precision', 'present', 'product', 'radix', 'ran', 'rand', 'random_number', 'random_seed', 'range', 'rank', 'rename', 'repeat', 'reshape', 'rrspacing', 'rshift', 'same_type_as', 'scale', 'scan', 'secnds', 'second', 'selected_char_kind', 'selected_int_kind', 'selected_real_kind', 'set_exponent', 'shape', 'shifta', 'shiftl', 'shiftr', 'sign', 'signal', 'sin', 'sinh', 'size', 'sizeof', 'sleep', 'spacing', 'spread', 'sqrt', 'srand', 'stat', 'storage_size', 'sum', 'symlnk', 'system', 'system_clock', 'tan', 'tanh', 'this_image', 'time', 'time8', 'tiny', 'trailz', 'transfer', 'transpose', 'trim', 'ttynam', 'ubound', 'ucobound', 'umask', 'unlink', 'unpack', 'verify', 'xor']
	keywords['special'] = ['in','out','inout','none'] # Removed ['logical','real'] to avoid collision with types
	typeparams = ['kind','len']
	operators = [r'[*][*]',r'[+]',r'[-]',r'[*]','==','/=', '//', '=&gt;','&gt;=','&lt;=','&gt;', '&lt;', r'[/]',r'\.and\.',r'\.or\.','\.not\.','\.eqv\.','\.neqv\.']

	# Later we need to be able to look up which catergory a word belongs to
	lookup = {}
	for category in keywords:
		for word in keywords[category]:
			lookup[word.replace('[','').replace(']','').replace('\\','')] = category

	# Find procedure names
	subroutines = re.findall(r'\bsubroutine ([^(]*)\(', code)
	functions = re.findall(r'\bfunction ([^(]*)\(', code)

	for subroutine in subroutines:
		code = re.sub(r'\b(%s)\b'%subroutine,lambda m:r'<subname>%s</subname>'%m.group(0),code)

	for function in functions:
		code = re.sub(r'\b(%s)\b'%function,lambda m:r'<funcname>%s</funcname>'%m.group(0),code)

	# Find comments
	code = re.sub(r'!.*',lambda m:'<comment>%s</comment>'%m.group(0),code)

	# Find constants
	# BUG: Doesn't handle kinds, complex, allows malformed numbers
	code = re.sub(r"""('[^'\n]*?'|"[^"\n]*?"|(\b|-)\d+?\b|\true\.|\.false\.)""",lambda m:'<literal>%s</literal>'%m.group(0),code)

	# Find operators
	code = re.sub(r'(?<=[^<])(%s)'%'|'.join(operators),lambda m: '<operator>%s</operator>'%m.group(1),code)

	# Find derived types
	dertypes = re.findall(r'type \b(.*)\b', code)
	if len(dertypes) > 0:
		code = re.sub(r'\b('+'|'.join(dertypes)+r')\b',lambda m:r'<typename>%s</typename>'%m.group(0),code)
	
	dertypes = re.findall(r'type, extends\(.*\)\s*::\s*\b(.*)', code)
	if len(dertypes) > 0:
		code = re.sub(r'\b('+'|'.join(dertypes)+r')\b',lambda m:r'<typename>%s</typename>'%m.group(0),code)

	# BUG: Should be done per-procedure/module/block
	arrays = []
	scalars = []
	# Find variable types
	for vardef in re.findall(r'\n(.*)::(.*?)(?=\n)', code):
		if 'type' in vardef[0] and 'extends' in vardef[0]:
			continue
		for var in vardef[1].split(','):
			if '=' in var: # Don't include assigment in type name
				var = var.split('=')[0]
			if 'dimension' in vardef[0]: # If we have dimensions it's an array
				arrays.append(var.strip())
			else:
				scalars.append(var.strip())

	# Add implicitly declared variables
	# ...in forall
	for vardef in re.findall(r'\b(?:forall|do concurrent)\s*\((.*)\)',code):
		for var in vardef.split('=')[:-1]:
			scalars.append(var.split(',')[-1].strip())

	# ...in result
	# BUG: Might not be scalar
	for vardef in re.findall(r'result\s*\((.*)\)',code):
		scalars.append(vardef)

	if len(arrays) > 0:
		code = re.sub(r'\b(%s)\b'%('|'.join(arrays)), lambda m:r'<arrvar>%s</arrvar>'%m.group(0),code)
	if len(scalars) > 0:
		code = re.sub(r'\b(%s)\b'%('|'.join(scalars)), lambda m:r'<scalarvar>%s</scalarvar>'%m.group(0),code)

	# Find type parameters
	code = re.sub(r'\((.*)\)(\s*::)',lambda m: r'(%s)%s'%(re.sub('(%s)='%'|'.join(typeparams),r'<typeparam>\1</typeparam>=',m.group(1)),m.group(2)),code)

	# Find keywords
	allkeywords = list(itertools.chain(*(keywords.values())))
	code = re.sub(r'(?<=[ \n,()=:;])('+'|'.join(allkeywords)+r')(?=[ \n,()=:;])', lambda m: r'<%s>%s</%s>'%(lookup[m.group(1)],m.group(1),lookup[m.group(1)]), code)

	# Remove tags from inside comments and strings
	def strip_tags(s):
		return re.sub(r'<.+?>','',s)
	code = re.sub(r'(<comment>)(.*?)(<\/comment>)',lambda m: m.group(1)+strip_tags(m.group(2))+m.group(3),code)
	code = re.sub(r'(<literal>)(.*?)(<\/literal>)',lambda m: m.group(1)+strip_tags(m.group(2))+m.group(3),code)

	# Convert to HTML
	def process(s):
		return re.sub(r'<([^>]+?)>(.+?)</\1>',lambda m: r'<span class="%s">%s</span>'%(m.group(1),process(m.group(2))), s)
	code = process(code)
	
	#Linkify intrinsics to GCC docs
	code = re.sub('(?<=<span class="intrinsic">)([^<]+)',lambda m: r'<a href="http://gcc.gnu.org/onlinedocs/gfortran/%s.html">%s</a>'%(m.group(1).upper(),m.group(1)),code)

	return code

def main():
	html = sys.stdin.read()

	# Compile all examples to check that it works
	for m in re.findall(r'<pre><code>(.*?)</code></pre>',html,re.DOTALL):
		m = m.replace('&gt;','>').replace('&lt;','<')
		f = tempfile.NamedTemporaryFile(delete=False,prefix='fort',suffix='.f90')
		name = f.name
		f.write(m.encode('utf-8'))
		f.close()
		try:
			#print(subprocess.check_output(['gfortran','-std=f2008',name]), file=sys.stderr)
			print(subprocess.check_output(['gfortran','-std=f2008','-Wall','-Wextra',name]), file=sys.stderr)
		except:
			pass

	html = re.sub('(?<=<pre><code>)(.*?)(?=</code></pre>)', lambda m: tag(m.group(1)), html, flags=re.DOTALL)

        toc="<section id='toc'>"
        prev_level = 0
        for m in re.findall(r'<h([234])>(.*)</h', html):
            level = int(m[0])
            if level > prev_level:
                toc += '\n'
                toc += ' '*(level - 1)
                toc += '<ul>\n'
            elif level == prev_level:
                toc += '</li>\n'
            elif level < prev_level:
                toc += '</li>\n'
                toc += ' '*level
                toc += '</ul>\n'
            prev_level = level

            toc += ' '*level
            toc += '<li>' + m[1]

        toc += '\n </ul>'
        toc += '\n</ul>'
        toc += '</section>'
        html = html.replace("<section id='toc'/>", toc)
	print(html)

if __name__ == '__main__':
	main()
