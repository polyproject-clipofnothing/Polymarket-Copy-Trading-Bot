locals {
  project = "polymarket-copy-trading-bot"

  tags = {
    Project   = local.project
    ManagedBy = "terraform"
    Env       = var.env
  }
}
