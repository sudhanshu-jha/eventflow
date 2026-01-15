from setuptools import setup, find_packages

requires = [
    'pyramid>=2.0',
    'pyramid_tm',
    'SQLAlchemy>=2.0',
    'psycopg2-binary',
    'alembic',
    'graphene>=3.0',
    'graphene-sqlalchemy',
    'celery[redis]>=5.0',
    'redis',
    'PyJWT>=2.0',
    'bcrypt',
    'python-dotenv',
    'waitress',
    'cornice',
    'marshmallow',
    'requests',
]

testing_requires = [
    'pytest',
    'pytest-cov',
    'webtest',
]

setup(
    name='analytics',
    version='1.0.0',
    description='Async Analytics & Notification Platform',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    extras_require={
        'testing': testing_requires,
    },
    entry_points={
        'paste.app_factory': [
            'main = analytics:main',
        ],
    },
)
