from setuptools import setup, find_packages

VERSION = '1' 
DESCRIPTION = 'A nespaper3k haystack wrapper, scraper and crawler'
LONG_DESCRIPTION = 'This package installs to classes for two haystack nodes that wrap the nespaper3k library, one for scraping websites and one for crawling while scraping.'

setup(

        name="src", 
        version=VERSION,
        author="haradai",
        author_email="<josem.rocafortf@gmail.com>",
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        packages=find_packages(),
        install_requires=['haystack','newspaper3k','beautifulsoup4','tqdm'], 
        keywords=['haystack', 'newspaper3k'],
        classifiers= [
            "Development Status :: 3 - Alpha",
            "Programming Language :: Python :: 3",
            "Operating System :: MacOS :: MacOS X",
        ]
)