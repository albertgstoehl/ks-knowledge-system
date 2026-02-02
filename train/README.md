# Train Service

Personal training and marathon preparation service.

## Runalyze Integration

Train syncs training analytics from Runalyze (which receives data from Garmin Connect).

### Setup

1. Sign up for Runalyze Supporter (€2.50/mo)
2. Connect Garmin Connect account to Runalyze
3. Get Personal API token from Runalyze settings
4. Add token to K8s secret:
   ```bash
   kubectl create secret generic runalyze-credentials \
     --from-literal=token=YOUR_TOKEN \
     -n knowledge-system
   ```

### Manual Sync

```bash
cd train
export RUNALYZE_TOKEN=your_token
export TRAIN_API_URL=http://localhost:8000
python scripts/sync_runalyze.py --days 7
```

### Metrics Synced

- **Marathon Shape**: % readiness for marathon distance
- **TSB**: Training Stress Balance (fatigue vs fitness)
- **VO2max**: Effective aerobic capacity estimate
- **ATL/CTL**: Fatigue and fitness trends
- **Health**: Sleep, HRV, resting HR (from Garmin via Runalyze)

## Development

```bash
cd train
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

## Tests

```bash
cd train
PYTHONPATH=src python3 -m pytest tests/ -v
```
