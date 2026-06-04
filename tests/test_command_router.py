"""Testes para app/command_router.py"""

from app.command_router import CommandRouter


def test_register_and_dispatch():
    """Registrar e executar comando."""
    router = CommandRouter()

    results = []

    def my_cmd(*, args, **kw):
        results.append(("executed", args))
        return True

    router.register("testar", my_cmd, "Comando de teste")

    # Disparar
    result = router.dispatch("/testar arg1 arg2")
    assert result is True
    assert results[0] == ("executed", "arg1 arg2")


def test_unknown_command():
    """Comando nao registrado retorna False."""
    router = CommandRouter()
    result = router.dispatch("/desconhecido")
    assert result is False


def test_not_a_command():
    """Texto sem / nao e comando."""
    router = CommandRouter()
    result = router.dispatch("mensagem normal")
    assert result is False


def test_list_commands():
    """Listagem de comandos."""
    router = CommandRouter()
    router.register("cmd1", lambda **kw: True, "Desc 1")
    router.register("cmd2", lambda **kw: True, "Desc 2")

    cmds = router.list_commands()
    assert len(cmds) == 2
    assert ("/cmd1", "Desc 1") in cmds


def test_is_command():
    """Detectar se texto parece comando."""
    router = CommandRouter()
    assert router.is_command("/status")
    assert router.is_command("/ajuda")
    assert not router.is_command("mensagem normal")
    assert not router.is_command(" /status")  # espaco antes
