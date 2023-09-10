
# About
This project aims to create simple songbook for storing, managing and viewing songs with their respective chords. The songs are loaded once and then all filtering/searching happens on the client which means it is usable even in conditions with low or almost no internet access as it can be preloaded. The site can also generate PDF files from selected songs for offline viewing or printing.

# Getting Started

First clone the repository from Github and switch to the new directory:

    $ git clone https://github.com/pehala/song-book.git
    $ cd song-book
    
Install pipenv and dependencies

    $ python -m pip install poetry
    $ poetry install 
    
Then simply initialize the website:

    $ make init

You can now run the development server:

    $ make run

## FAQ

1. pipenv install throws 

       ERROR: Couldn't install package: rcssmin
       Package installation failed...

    Install apt-get install python3-dev (or yum install python3-devel etc.)

