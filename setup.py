from setuptools import setup, find_packages

setup(
    name='snyk-code-debug',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'snyk-code-debug = snyk_code_debug.snyk_code_debug:main_function'
        ]
    },
        author='Sebastian Roth',
    author_email='sebastian.roth@snyk.io',
    description='Snyk Code debug script to determine files that failed analysis',
    url='http://github.com/sebsnyk/snyk-code-debug',
)
