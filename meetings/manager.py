import click
import code


@click.group()
def cli():
    pass


@cli.command()
@click.pass_context
@click.option('-h', '--host', default='127.0.0.1')
@click.option('-p', '--port', default=5000)
def runserver(ctx, host, port):
    app = ctx.obj['app']
    app.run(host, port)


@cli.command()
@click.pass_context
def shell(ctx):
    context = dict(app=ctx.obj['app'])
    try:
        from bpython import embed
        embed(locals_=context)
        return
    except ImportError:
        pass
    code.interact(local=context)
