# Wikirumours

# Create a database in MySql
Create a database in MySQL and input the correct env values in the .env file
This is mentioned under the . env file section
Optional: Check the connection details in base_settings.py for the database connection.

# Extra packages required for mysqlclient
	sudo apt install mysql-server
	sudo apt-get install python3-dev default-libmysqlclient-dev build-essential'

# Extra packages required for google maps
	sudo apt-get install binutils libproj-dev gdal-bin'
    
# Virtual environment
We recommend creating a virtual env for all the python dependencies.
	
# Install the dependencies from requirements.txt
	pip install -r requirements.txt

# Run the database migrations 
	python manage.py migrate

# Create the cachetable for regulating ip addresses
	python manage.py createcachetable

# To set up Celery for running automatic backups
To configure and celery you need first install and configure redis server
Once set up just update the redis ip on the .env file
To run celery on windows open another powershell or linux terminal or a cmd tab in the project root and run the command

	celery -A wikirumours worker --pool=solo -l info


And on another terminal run the celery beat

	celery -A wikirumours beat -l info


Backups will be stored inside the server in a backups folder just outside the project root
To run manual backups use the command

	python manage.py dbbackup


To manually restore a backup

	python manage.py dbrestore

The latest backup should be restored to the database


# To start the server
	python manage.py runserver 0.0.0.0:8000

# To create superuser
	python manage.py createsuperuser

# .env file
Create a .env file in the root folder with the following keys along with their appropriate values

	REDIS_IP = 
	GOOGLE_MAP_API_KEY=
	MAPBOX_API_KEY=
	DATABASE_NAME=
	DATABASE_USER=
	DATABASE_PASSWORD=
	DATABASE_HOST=



# (Optional) Import data script
Export the production database tables as csvs.

Export options should be "export tables as separate files" and "Include header row".

Copy the files into "wikirumours/users/management/data" folder

Run

	 `python manage.py import_all_csvs`
	

