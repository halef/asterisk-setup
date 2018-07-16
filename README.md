# asterisk - Installation and configuration update

This repo contains some scripts I use to install Asterisk with a stripped down configuration. These have been
used for personal projects and it is advisable to review the content of the scripts before running them
yourself.

## Note

Parameters are currently hard-coded inside the scripts. Please check the scripts what is installed and where
it is installed to. This should be made configurable enventually.

## Scripts

- install.sh     :  Installs asterisk
- update-conf.sh :  Updates asterisk configuration with content of conf/ directory. 
- helper.sh      :  Some helper functions. Mostly taken from https://github.com/langep/bash_helpers/. Probably should replace this with a submodule at some point.


