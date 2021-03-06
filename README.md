# Amazon Order History Web Scraper
Uses Selenium to simulate login and going through all the users orders. Saves the received data in a json
file for later evaluation.

Currently only works for the german version of Amazon (amazon.de). For amazon.com users there is already a built in feature to export your data to a csv file.

# Install
1) clone the repo `https://github.com/MaX-Lo/Amazon-Order-History.git`

2) install requirements `pip install -r requirements.txt`

3) Make sure your [Geckodriver](https://github.com/mozilla/geckodriver/releases/tag/v0.24.0 "Geckodriver Releases")
is installed and on your PATH variable.
For convenience there is a bash script in the project root dir for that.
This script downloads the latest version of geckodriver, makes it executable and puts in the /usr/share/bin which is 
already in the PATH by default. It need sudo permission to do so though. 
For the Skript run: 

`chmod +x geckodriver_installer.sh`

`./geckodriver.sh`.

# Usage
If you are using a device where you've never logged in before, Amazon might require a confirmation code from an email
it has send to you. Therefore it can be necessary to log into Amazon with your browser before using that script on a new device. 
After logging in the first time there shouldn't be anymore email confirmations necessary. The same applies if you
have two-factor authentication activated.

## Scraping

`python -m scraping scrape --email abc@xy.z --password 123`

If you don't want your password appearing in the bash history or on the terminal output, you can create a `pw.txt` in 
the project root directory (`Amazon-Order-History`), which contains your password and don't use the password parameter.


In case of import errors pay attention to start the script from the main folder (Scraping) and not from inside Scraping/scraping

## Evaluation
`python -m scraping dash` starts a flask server (should be under http://127.0.0.1:8050/)


## Help

There are some optional parameters available, `python -m scraping --help` shows a description for each of them.
