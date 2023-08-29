from flask.cli import FlaskGroup

from app import APP


cli = FlaskGroup(APP)


if __name__ == '__main__':
    cli()