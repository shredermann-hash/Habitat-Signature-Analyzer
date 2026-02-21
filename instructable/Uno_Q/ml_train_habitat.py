#!/usr/bin/env python3
"""
Habitat Signature V2 - Training FINAL
V2 : 14 features (ajout proximity_mean, proximity_max)
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import json
import glob
import os

print("===================================")
print("  HABITAT SIGNATURE V2 - TRAINING")
print("===================================\n")

files = glob.glob('/home/arduino/ml_data/habitat_*.csv')

if len(files) == 0:
    print("Aucun fichier habitat_*.csv trouve")
    exit(1)

dfs = []
groups = []

for idx, f in enumerate(files):
    df = pd.read_csv(f)
    dfs.append(df)
    groups.extend([idx] * len(df))
    label = f.split('habitat_')[1].split('_')[0]
    print(f"  Session {idx:2d} | {label:10s} | {len(df)} fenetres")

data = pd.concat(dfs, ignore_index=True)
groups = np.array(groups)

# Features (14) - ordre fixe
feature_cols = [
    'audio_rms_mean', 'audio_rms_var', 'audio_rms_delta',
    'audio_zcr_mean', 'audio_zcr_var',
    'imu_norm_mean',  'imu_norm_var',
    'mag_norm_mean',  'mag_norm_var',
    'pressure_mean',  'pressure_grad',
    'corr_audio_imu',
    'proximity_mean', 'proximity_max',
]

# Anciennes sessions sans proximity -> remplir avec 0
for col in ['proximity_mean', 'proximity_max']:
    if col not in data.columns:
        data[col] = 0.0

print(f"\nVerification NaN...")
if data[feature_cols].isnull().any().any():
    nan_count = data[feature_cols].isnull().sum().sum()
    print(f"   {nan_count} NaN detectes -> suppression lignes")
    mask = ~data[feature_cols].isnull().any(axis=1)
    data = data[mask].reset_index(drop=True)
    groups = groups[mask.values]
else:
    print(f"   Aucun NaN detecte")

print(f"\nTotal     : {len(data)} fenetres")
print(f"Sessions  : {len(files)}")
print(f"Distribution:")
for label, count in data['label'].value_counts().items():
    print(f"   {label:10s} : {count:4d} ({count/len(data)*100:.1f}%)")

X = data[feature_cols].values
y = data['label'].values

classes = sorted(np.unique(y))
print(f"\nClasses : {classes}")

# Split manuel : 1 session test par classe
test_sessions = []
for label in np.unique(y):
    label_sessions = np.unique(groups[y == label])
    test_sessions.append(int(label_sessions[-1]))
test_sessions = np.array(test_sessions)
print(f"   Sessions test : {test_sessions}")
test_mask = np.isin(groups, test_sessions)
test_idx = np.where(test_mask)[0]
train_idx = np.where(~test_mask)[0]

X_train, X_test = X[train_idx], X[test_idx]
y_train, y_test = y[train_idx], y[test_idx]
groups_train = groups[train_idx]

print(f"\nGroupShuffleSplit:")
print(f"   Train : {len(X_train)} fenetres | {len(np.unique(groups_train))} sessions")
print(f"   Test  : {len(X_test)} fenetres  | {len(np.unique(groups[test_idx]))} sessions")

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('rf', RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_leaf=3,
        random_state=42,
        class_weight='balanced',
        n_jobs=-1
    ))
])

n_splits = min(5, len(np.unique(groups_train)))
print(f"\nGroupKFold CV (n={n_splits})...")

if n_splits >= 2:
    gkf = GroupKFold(n_splits=n_splits)
    cv_scores = cross_val_score(pipeline, X_train, y_train, cv=gkf, groups=groups_train)
    print(f"   Scores : {[f'{s*100:.1f}%' for s in cv_scores]}")
    print(f"   Mean   : {cv_scores.mean()*100:.1f}% +/- {cv_scores.std()*100:.1f}%")
    cv_mean = float(cv_scores.mean())
    cv_std  = float(cv_scores.std())
else:
    print("   Pas assez de sessions (besoin 2+)")
    cv_mean = 0.0
    cv_std  = 0.0

print(f"\nEntrainement final...")
pipeline.fit(X_train, y_train)

y_pred   = pipeline.predict(X_test)
accuracy = pipeline.score(X_test, y_test)

print(f"\nTest Accuracy : {accuracy*100:.1f}%")

print("\nClassification Report:")
print(classification_report(y_test, y_pred, labels=classes))

print("Confusion Matrix:")
print(f"{'':12s}", end='')
for l in classes:
    print(f"{l:12s}", end='')
print()
cm = confusion_matrix(y_test, y_pred, labels=classes)
for i, l in enumerate(classes):
    print(f"{l:12s}", end='')
    for j in range(len(classes)):
        print(f"{cm[i,j]:12d}", end='')
    print()

print("\nFeature Importance:")
importances = sorted(
    zip(feature_cols, pipeline.named_steps['rf'].feature_importances_),
    key=lambda x: x[1], reverse=True
)
for feat, imp in importances:
    bar = '#' * int(imp * 50)
    print(f"   {feat:20s} {imp:.3f} {bar}")

os.makedirs('/home/arduino/ml_models', exist_ok=True)

joblib.dump(pipeline, '/home/arduino/ml_models/habitat_signature_pipeline.pkl')

config = {
    'classes':           classes,
    'features':          feature_cols,
    'n_features':        len(feature_cols),
    'accuracy':          float(accuracy),
    'cv_mean':           cv_mean,
    'cv_std':            cv_std,
    'n_sessions':        len(files),
    'n_samples_total':   len(data),
    'n_samples_train':   len(X_train),
    'n_samples_test':    len(X_test),
    'trained_at':        pd.Timestamp.utcnow().isoformat()
}

with open('/home/arduino/ml_models/habitat_signature_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print(f"\nPipeline sauvegarde (14 features):")
print(f"   habitat_signature_pipeline.pkl")
print(f"   habitat_signature_config.json\n")
