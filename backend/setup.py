from setuptools import setup, find_packages

setup(
    name='cyberhunter_3d',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'Flask',
        'Flask-SQLAlchemy',
        'Flask-Login',
        'Flask-Bcrypt',
        'pyotp',
        'qrcode[pil]',
        'requests',
        'PyYAML',
        'pytest',
    ],
    entry_points={
        'console_scripts': [
            'cyberhunter=cyberhunter_3d.main:main',
        ],
    },
)
