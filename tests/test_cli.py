"""El punto de entrada `cli.py`: el analizador de argumentos se construye y cada subcomando muestra su ayuda."""
import argparse
import importlib.util
import unittest

from tests.ayudas import PROYECTO

_spec = importlib.util.spec_from_file_location("cli_raiz", PROYECTO / "cli.py")
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


class Analizador(unittest.TestCase):
    def test_se_construye_y_toda_la_ayuda_es_valida(self):
        """Un `%` suelto en un texto de ayuda hace fallar el arranque entero (`badly formed help string`)."""
        parser = cli._parser()
        parser.format_help()
        subparsers = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
        self.assertIn("sesion", subparsers.choices)
        for nombre, sub in subparsers.choices.items():
            with self.subTest(nombre):
                sub.format_help()


if __name__ == "__main__":
    unittest.main()
