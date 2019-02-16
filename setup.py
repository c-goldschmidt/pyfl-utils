from distutils.core import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='pyfl_utils',
    version='0.0.1',
    license='WTFPL',
    description='Python library for Freelancer data structures',
    long_description=readme(),
    url='https://github.com/c-goldschmidt/pyfl-utils',
    author='CG',
    author_email='',
    maintainer='CG',
    maintainer_email='',
    packages=['pyfl_utils', 'pyfl_utils/models'],
    data_files=[
        ('share/pyfl_utils', ['README.md']),
    ],
    requires=['numpy (>=1.11.1)', 'Pillow (>=3.3.1)']
)
