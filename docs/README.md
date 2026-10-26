# Django Shop documentation

These pages explain how Django Shop is built, app by app. If you only have a few minutes, read the [architecture](architecture.md) and the [data model](data-model.md) first; every other page builds on them.

> The diagrams are written in [Mermaid](https://mermaid.js.org/), which GitHub renders directly.

## Start here

| Page | What it covers |
|---|---|
| [Architecture](architecture.md) | How the apps fit together, the life of a request, cross-cutting concerns and design decisions |
| [Data model](data-model.md) | Every model and relationship, delete rules and status lifecycles |

## The apps

| App | What it does |
|---|---|
| [accounts](apps/accounts.md) | Phone-based users, profiles, verification, password flows |
| [products](apps/products.md) | Catalog, categories, discounts, comments, images |
| [carts](apps/carts.md) | Shopping carts with stock validation |
| [orders](apps/orders.md) | Checkout, orders and invoices |
| [tickets](apps/tickets.md) | Support tickets and conversations |
| [userfav](apps/userfav.md) | Favorite products |
| [multimedia](apps/multimedia.md) | Video uploads, stories and highlights |

## Features and operations

| Page | What it covers |
|---|---|
| [Payments](payments.md) | The Zibal integration and how a payment is verified |
| [Admin panel](admin-panel.md) | Dashboard, user dossier, activity feed and reports |
| [Audit trail](history-audit.md) | How every change is recorded and reconstructed |
| [Testing](testing.md) | The test suite and how to run it |
| [Deployment](deployment.md) | Docker, environment variables and production settings |
| [Limitations](limitations.md) | What the project does not do yet, and what comes next |