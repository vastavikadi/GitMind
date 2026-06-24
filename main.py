import os
import typer

app = typer.Typer()

my_name = os.getenv("My_Name")
print(f"My name is {my_name}")