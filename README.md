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

# To start the server
	python manage.py runserver 0.0.0.0:8000

# To create superuser
	python manage.py createsuperuser

# .env file
Create a .env file in the root folder with the following keys along with their appropriate values

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
	
