import tkinter as tk

from formulario import main as formulario_main


def main():
    root = tk.Tk()
    formulario_main(root)
    root.mainloop()

if __name__ == "__main__":
    main()
