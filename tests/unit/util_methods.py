from solver_rewards.models.transfer import Transfer


def redirected_transfer(token, recipient, amount_wei, redirect) -> Transfer:
    # simple way to set up a transfer object with non-empty
    # redirect target field (for testing)
    transfer = Transfer(token, recipient, amount_wei)
    transfer._recipient = redirect
    return transfer
