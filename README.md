# MoneroAna

This repository includes codes and documents related to a
[Monero Fund research project](https://monerofund.org/projects/eae_attack_and_churning)
and is grateful to the donors, engineers, and administrators who made it possible.

The code relies on an instance of the [Onion Monero Explorer](https://github.com/moneroexamples/onion-monero-blockchain-explorer) and [Monero](https://github.com/monero-project/monero) running on the default ports.  

For the sake of reproducibility and transparency a partial collection of my transactions is included, please redact that usually-private information for publications.

An initial exploration, see the jupyter notebook in the demos 1001 blocks, shows that the decoys appears to be working quite well. 
With only 4 hops, around a 1/3 of the total blockchain is already included in a transaction's Taint Tree.
The intersections of possible co-origins of two given transactions is considerable, 100s of possibilities exist. 
This was true for both correlated and uncorrelated transactions.

Further efforts will expand upon these initial statistics and aide in quantifying the anonymity of the Monero Blockchain.

