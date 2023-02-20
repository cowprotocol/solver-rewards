from src.models.transfer import Transfer


def redirected_transfer(token, solver, amount_wei, redirect) -> Transfer:
    # simple way to set up a transfer object with non-empty
    # redirect target field (for testing)
    transfer = Transfer(token, solver, amount_wei)

    transfer._redirect_target = redirect
    return transfer
