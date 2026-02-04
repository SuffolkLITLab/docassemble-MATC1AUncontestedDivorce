import os
import sys
from setuptools import setup, find_namespace_packages
from fnmatch import fnmatchcase
from distutils.util import convert_path

standard_exclude = ('*.pyc', '*~', '.*', '*.bak', '*.swp*')
standard_exclude_directories = ('.*', 'CVS', '_darcs', './build', './dist', 'EGG-INFO', '*.egg-info')

def find_package_data(where='.', package='', exclude=standard_exclude, exclude_directories=standard_exclude_directories):
    out = {}
    stack = [(convert_path(where), '', package)]
    while stack:
        where, prefix, package = stack.pop(0)
        for name in os.listdir(where):
            fn = os.path.join(where, name)
            if os.path.isdir(fn):
                bad_name = False
                for pattern in exclude_directories:
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        break
                if bad_name:
                    continue
                if os.path.isfile(os.path.join(fn, '__init__.py')):
                    if not package:
                        new_package = name
                    else:
                        new_package = package + '.' + name
                        stack.append((fn, '', new_package))
                else:
                    stack.append((fn, prefix + name + '/', package))
            else:
                bad_name = False
                for pattern in exclude:
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        break
                if bad_name:
                    continue
                out.setdefault(package, []).append(prefix+name)
    return out

setup(name='docassemble.MATC1AUncontestedDivorce',
      version='1.24',
      description=('An in-progress collection of forms related to 1A uncontested divorces in MA (including: Joint Divorce Petition, Separation Agreement, Financial Forms, Child Custody, and other relevant documents)'),
      long_description='# docassemble.ADivorceAgreement\r\n\r\n1A Divorce Agreement\r\n\r\n## Author\r\n\r\nauthor@example.com\r\n\r\n',
      long_description_content_type='text/markdown',
      author='KP Hunsinger, Alara Akisik, Sam Darkwa Jr.',
      author_email='litlab@suffolk.edu',
      license='MIT',
      url='https://courtformsonline.org',
      packages=find_namespace_packages(),
      install_requires=['docassemble.ALMassachusetts>=0.1.2', 'docassemble.AssemblyLine @ git+https://github.com/SuffolkLITLab/docassemble-AssemblyLine.git@main'],
      zip_safe=False,
      package_data=find_package_data(where='docassemble/MATC1AUncontestedDivorce/', package='docassemble.MATC1AUncontestedDivorce'),
     )
