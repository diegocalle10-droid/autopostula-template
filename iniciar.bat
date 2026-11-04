@echo off
rem Lanza la captura con un doble clic: pregunta cuántas horas (vacío = horas_por_defecto de inputs\lotes.md),
rem avisa por Telegram al terminar y apaga el PC pasados apagar_tras_captura_min minutos (shutdown /a lo cancela).
cd /d "%~dp0"
python cli.py run-continuo
echo.
echo La captura ha terminado. Si no lo cancelas con "shutdown /a", el PC se apagara en unos minutos.
pause
