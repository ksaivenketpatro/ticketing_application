Pre Requisites:

1. Anaconda : https://docs.anaconda.com/anaconda/install/windows/ Install.
2. Open Anaconda command prompt from windows search bar


Install python packages
Type this command in the the command prompt
-> pip install flask

Now, go to the ticket generator or ticket verification directory 
Using "cd" command in the prompt
Eg: cd project/[folder name]

After reaching the directory, type the command
Ticket Generator
-> flask run --port=5001
You should then be able to see a URL, something like this - http://127.0.0.1:5001/ 
Click on that and you should be able to access it 

Ticket Verifier
-> python ver_app.py
You should then be able to see a URL, something like this - http://127.0.0.1:5000/ 