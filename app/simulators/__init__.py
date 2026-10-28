"""Simulated external systems: merchants, payment provider, courier.

These stand in for parties outside Trollie. They keep their own state in `sim_*`
tables, are driven through the same adapter contracts a real integration would use,
and support fault injection. Nothing here is evidence of any real partner capability.
"""
