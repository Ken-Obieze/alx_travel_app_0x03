from setuptools import setup, find_packages

setup(
    name="alx_travel_app",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        # List your project dependencies here
        'Django>=4.2.0',
        'djangorestframework',
        'drf-yasg',
        'python-dotenv',
        'django-environ',
    ],
)
