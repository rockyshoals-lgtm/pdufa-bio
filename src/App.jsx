import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Calendar,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  X,
  Filter,
  Search,
  Clock,
  Shield,
  Zap,
  Target,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  ExternalLink,
  DollarSign,
  Users,
  MessageCircle,
  PieChart,
  Flame,
  Eye,
  Bell,
  Brain,
  Briefcase,
  Heart,
  Info,
  Loader,
  ChevronRight,
  CheckSquare,
  Square,
} from 'lucide-react';

// ═══════════════════════════════════════════════════
// CATALYST DATA — ODIN v10.66 Dynamic Grandmaster
// ═══════════════════════════════════════════════════
const CATALYSTS_DATA = [
  {
    id: 'vnda-bysanti-2026-02-21',
    date: '2026-02-21',
    company: 'Vanda Pharmaceuticals',
    ticker: 'VNDA',
    drug: 'Bysanti (milsaperidone)',
    indication: 'Schizophrenia / Bipolar-I',
    type: 'PDUFA',
    appType: 'NDA',
    ta: 'CNS',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.5934,
    tier: 'TIER_4',
    taRisk: 'MOD_RISK',
    action: 'NO_POSITION',
    exit: 'N/A',
    runner: '0%',
    avoid: false,
    weekend: true,
    signals: {
      inexperienced_sponsor: -1.0450377464294434,
      ta_mod_risk: -0.18831130862236023,
    },
    totalAdj: -1.233349084854126,
    logit: 0.3780280351638794,
  },
  {
    id: 'otsuka-inqovi-venetoclax-2026-02-25',
    date: '2026-02-25',
    company: 'Otsuka',
    ticker: 'OTSKF',
    drug: 'INQOVI + Venetoclax',
    indication: 'Acute Myeloid Leukemia',
    type: 'PDUFA',
    appType: 'sNDA',
    ta: 'Oncology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9116,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      'sNDA/sBLA': -0.3978,
      experienced_sponsor: 0.7777,
      ta_low_risk: 0.1065,
      ind_cancer: 0.2351,
    },
    totalAdj: 0.07800000160932541,
    logit: 2.3328,
  },
  {
    id: 'regn-dupixent-afrs-2026-02-28',
    date: '2026-02-28',
    company: 'Regeneron / Sanofi',
    ticker: 'REGN',
    drug: 'Dupixent',
    indication: 'Allergic Fungal Rhinosinusitis',
    type: 'PDUFA',
    appType: 'sBLA',
    ta: 'Immunology',
    phase: 'Phase 3',
    designations: ['Priority Review'],
    enrollment: 0,
    nctId: '',
    prob: 0.9339,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      'sNDA/sBLA': -0.39780697226524353,
      priority_review: 0.5500093102455139,
      experienced_sponsor: 0.7777218222618103,
      ta_low_risk: 0.10649222880601883,
    },
    totalAdj: 1.0364164113998413,
    logit: 2.6477935314178467,
  },
  {
    id: 'asnd-navepegritide-2026-02-28',
    date: '2026-02-28',
    company: 'Ascendis Pharma',
    ticker: 'ASND',
    drug: 'Navepegritide (TransCon CNP)',
    indication: 'Achondroplasia',
    type: 'PDUFA',
    appType: 'BLA',
    ta: 'Rare Disease',
    phase: 'Phase 3',
    designations: ['Orphan Drug', 'Priority Review'],
    enrollment: 0,
    nctId: 'NCT05386264',
    avoid: false,
    prob: 0.9477,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    signals: {
      experienced_sponsor: 0.7777218222618103,
      orphan: 0.14541392028331757,
      priority_review: 0.5500093102455139,
      ta_mod_risk: -0.18831130862236023,
    },
    totalAdj: 1.2848337441682816,
    logit: 2.896210864186287,
    weekend: true,
  },
  {
    id: 'bmy-deucravacitinib-2026-03-06',
    date: '2026-03-06',
    company: 'Bristol-Myers Squibb',
    ticker: 'BMY',
    drug: 'Deucravacitinib (Sotyktu)',
    indication: 'Psoriatic Arthritis',
    type: 'PDUFA',
    appType: 'sNDA',
    ta: 'Immunology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.8907,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      'sNDA/sBLA': -0.3978,
      experienced_sponsor: 0.7777,
      ta_low_risk: 0.1065,
    },
    totalAdj: 0.057100001722574234,
    logit: 2.0978,
  },
  {
    id: 'aldx-reproxalap-2026-03-16',
    date: '2026-03-16',
    company: 'Aldeyra Therapeutics',
    ticker: 'ALDX',
    drug: 'Reproxalap',
    indication: 'Dry Eye Disease',
    type: 'PDUFA',
    appType: 'NDA',
    ta: 'Ophthalmology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.0275,
    tier: 'TIER_4',
    taRisk: 'HIGH_RISK',
    action: 'NO_POSITION',
    exit: 'N/A',
    runner: '0%',
    avoid: false,
    weekend: false,
    signals: {
      prior_CRL: -2.8551,
      inexperienced_sponsor: -1.045,
      hist_crl_rate: -0.5109,
      ta_high_risk: -0.2834,
      novice_high_risk_ta: -0.4837,
    },
    totalAdj: -0.8061000108718872,
    logit: -3.5667,
  },
  {
    id: 'rytm-imcivree-2026-03-20',
    date: '2026-03-20',
    company: 'Rhythm Pharmaceuticals',
    ticker: 'RYTM',
    drug: 'Imcivree (setmelanotide)',
    indication: 'Acquired Hypothalamic Obesity',
    type: 'PDUFA',
    appType: 'sNDA',
    ta: 'Metabolic/Endocrine',
    phase: 'Phase 3',
    designations: ['Orphan Drug'],
    enrollment: 0,
    nctId: '',
    prob: 0.5314,
    tier: 'TIER_4',
    taRisk: 'MOD_RISK',
    action: 'NO_POSITION',
    exit: 'N/A',
    runner: '0%',
    avoid: false,
    weekend: false,
    signals: {
      'sNDA/sBLA': -0.3978,
      inexperienced_sponsor: -1.045,
      orphan: 0.1454,
      ta_mod_risk: -0.1883,
    },
    totalAdj: -0.30219998955726624,
    logit: 0.1256,
  },
  {
    id: 'gsk-linerixibat-2026-03-24',
    date: '2026-03-24',
    company: 'GSK',
    ticker: 'GSK',
    drug: 'Linerixibat',
    indication: 'Cholestatic Pruritus (PBC)',
    type: 'PDUFA',
    appType: 'NDA',
    ta: 'GI/Hepatology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.916,
    tier: 'TIER_1',
    taRisk: 'HIGH_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
    },
    totalAdj: 0.08240000158548355,
    logit: 2.3891,
  },
  {
    id: 'lly-orforglipron-2026-03-25',
    date: '2026-03-25',
    company: 'Eli Lilly',
    ticker: 'LLY',
    drug: 'Orforglipron',
    indication: 'Type 2 Diabetes / Obesity',
    type: 'PDUFA (Expected)',
    appType: 'NDA',
    ta: 'Metabolic/Endocrine',
    phase: 'Phase 3',
    designations: ['National Priority Voucher'],
    enrollment: 0,
    nctId: '',
    prob: 0.94,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      priority_review: 0.55,
      experienced_sponsor: 0.7777,
      ta_mod_risk: -0.1883,
    },
    totalAdj: 0.10639999806880951,
    logit: 2.7508,
  },
  {
    id: 'iron-bitopertin-2026-03-25b',
    date: '2026-03-25',
    company: 'Disc Medicine',
    ticker: 'IRON',
    drug: 'Bitopertin',
    indication: 'Erythropoietic Protoporphyria',
    type: 'PDUFA (Expected)',
    appType: 'NDA',
    ta: 'Hematology',
    phase: 'Phase 3',
    designations: ['Orphan Drug', 'Breakthrough Therapy'],
    enrollment: 0,
    nctId: '',
    prob: 0.5238,
    tier: 'TIER_4',
    taRisk: 'HIGH_RISK',
    action: 'NO_POSITION',
    exit: 'N/A',
    runner: '0%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      BTD: 0.1505,
      orphan: 0.1454,
      ta_high_risk: -0.2834,
      novice_high_risk_ta: -0.4837,
    },
    totalAdj: -0.30979999899864197,
    logit: 0.0952,
  },
  {
    id: 'rckt-kresladi-2026-03-28',
    date: '2026-03-28',
    company: 'Rocket Pharmaceuticals',
    ticker: 'RCKT',
    drug: 'Kresladi (marnetegragene autotemcel)',
    indication: 'Leukocyte Adhesion Deficiency-I',
    type: 'PDUFA',
    appType: 'BLA',
    ta: 'Rare Disease',
    phase: 'Phase 1/2',
    designations: ['Orphan Drug', 'Breakthrough Therapy', 'Priority Review'],
    enrollment: 0,
    nctId: '',
    prob: 0.8774,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      inexperienced_sponsor: -1.045,
      BTD: 0.1505,
      orphan: 0.1454,
      priority_review: 0.55,
      class1_resub: 0.556,
    },
    totalAdj: 0.043800000101327896,
    logit: 1.9683,
  },
  {
    id: 'lnth-ga68-edotreotide-2026-03-29',
    date: '2026-03-29',
    company: 'Lantheus',
    ticker: 'LNTH',
    drug: 'Gallium-68 edotreotide',
    indication: 'NET PET Imaging',
    type: 'PDUFA',
    appType: 'NDA',
    ta: 'Oncology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.8479,
    tier: 'TIER_2',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      ta_low_risk: 0.1065,
    },
    totalAdj: 0.014299999922513962,
    logit: 1.7179,
  },
  {
    id: 'dnli-tividenofusp-2026-04-05',
    date: '2026-04-05',
    company: 'Denali Therapeutics',
    ticker: 'DNLI',
    drug: 'Tividenofusp alfa',
    indication: 'Hunter Syndrome (MPS II)',
    type: 'PDUFA',
    appType: 'BLA',
    ta: 'Rare Disease',
    phase: 'Phase 2/3',
    designations: ['Breakthrough Therapy', 'Orphan Drug', 'Priority Review'],
    enrollment: 63,
    nctId: 'NCT05371613',
    prob: 0.8041,
    tier: 'TIER_2',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      inexperienced_sponsor: -1.045,
      BTD: 0.1505,
      orphan: 0.1454,
      priority_review: 0.55,
    },
    totalAdj: -0.029500000178813934,
    logit: 1.4123,
  },
  {
    id: 'orca-orca-t-2026-04-06',
    date: '2026-04-06',
    company: 'Orca Bio',
    ticker: 'ORCA',
    drug: 'Orca-T',
    indication: 'Hematologic Malignancies (AML/ALL/MDS)',
    type: 'PDUFA',
    appType: 'BLA',
    ta: 'Oncology',
    phase: 'Phase 3',
    designations: ['Priority Review'],
    enrollment: 0,
    nctId: '',
    prob: 0.7726,
    tier: 'TIER_2',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      priority_review: 0.55,
      ta_low_risk: 0.1065,
    },
    totalAdj: -0.061000000685453415,
    logit: 1.2228,
  },
  {
    id: 'tvtx-sparsentan-2026-04-13',
    date: '2026-04-13',
    company: 'Travere Therapeutics',
    ticker: 'TVTX',
    drug: 'Sparsentan',
    indication: 'Focal Segmental Glomerulosclerosis (FSGS)',
    type: 'PDUFA',
    appType: 'sNDA',
    ta: 'Nephrology',
    phase: 'Phase 3',
    designations: ['Priority Review', 'Accelerated Approval conversion'],
    enrollment: 406,
    nctId: 'NCT03762850',
    prob: 0.608,
    tier: 'TIER_4',
    taRisk: 'HIGH_RISK',
    action: 'NO_POSITION',
    exit: 'N/A',
    runner: '0%',
    avoid: false,
    weekend: false,
    signals: {
      'sNDA/sBLA': -0.3978,
      inexperienced_sponsor: -1.045,
      priority_review: 0.55,
      accel_approval: 0.4875,
      ta_high_risk: -0.2834,
      novice_high_risk_ta: -0.4837,
    },
    totalAdj: -0.225600004196167,
    logit: 0.439,
  },
  {
    id: 'azn-baxdrostat-2026-05-15',
    date: '2026-05-15',
    company: 'AstraZeneca',
    ticker: 'AZN',
    drug: 'Baxdrostat',
    indication: 'Treatment-Resistant Hypertension',
    type: 'PDUFA (Expected)',
    appType: 'NDA',
    ta: 'Cardiovascular',
    phase: 'Phase 3',
    designations: ['Priority Review'],
    enrollment: 0,
    nctId: '',
    prob: 0.94,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      priority_review: 0.55,
      experienced_sponsor: 0.7777,
      ta_mod_risk: -0.1883,
    },
    totalAdj: 0.10639999806880951,
    logit: 2.7508,
  },
  {
    id: 'aclx-cytisinicline-2026-06-20',
    date: '2026-06-20',
    company: 'Achieve Life Sciences',
    ticker: 'ACHV',
    drug: 'Cytisinicline',
    indication: 'Smoking Cessation',
    type: 'PDUFA',
    appType: 'NDA',
    ta: 'CNS',
    phase: 'Phase 3',
    designations: ['Breakthrough Therapy'],
    enrollment: 0,
    nctId: '',
    prob: 0.6291,
    tier: 'TIER_3',
    taRisk: 'MOD_RISK',
    action: 'SMALL_POSITION_EARLY_EXIT',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      inexperienced_sponsor: -1.0450377464294434,
      BTD: 0.15052397549152374,
      ta_mod_risk: -0.18831130862236023,
    },
    totalAdj: -1.0828250646591187,
    logit: 0.5285520553588867,
  },
  {
    id: 'vrdn-veligrotug-2026-06-30',
    date: '2026-06-30',
    company: 'Viridian Therapeutics',
    ticker: 'VRDN',
    drug: 'Veligrotug',
    indication: 'Thyroid Eye Disease',
    type: 'PDUFA',
    appType: 'BLA',
    ta: 'Immunology',
    phase: 'Phase 3',
    designations: ['Priority Review'],
    enrollment: 0,
    nctId: '',
    prob: 0.7726,
    tier: 'TIER_2',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.0450377464294434,
      priority_review: 0.5500093102455139,
      ta_low_risk: 0.10649222880601883,
    },
    totalAdj: -0.3885362148284912,
    logit: 1.2228409051895142,
  },
  {
    id: 'kura-tipifarnib-2026-07-01',
    date: '2026-07-01',
    company: 'Kura Oncology',
    ticker: 'KURA',
    drug: 'Tipifarnib',
    indication: 'HRAS-mutant HNSCC',
    type: 'PDUFA',
    appType: 'NDA',
    ta: 'Oncology',
    phase: 'Phase 2',
    designations: ['Breakthrough Therapy', 'Orphan Drug', 'Priority Review'],
    enrollment: 63,
    nctId: 'NCT02383927',
    prob: 0.8204,
    tier: 'TIER_2',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      BTD: 0.1505,
      orphan: 0.1454,
      priority_review: 0.55,
      ta_low_risk: 0.1065,
    },
    totalAdj: -0.013199999928474426,
    logit: 1.5188,
  },
  {
    id: 'gsk-varicella-vaccine-2026-07-01',
    date: '2026-07-01',
    company: 'GSK',
    ticker: 'GSK',
    drug: 'Varicella vaccine (investigational)',
    indication: 'Chickenpox',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Vaccines',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.916,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
    },
    totalAdj: 0.08240000158548355,
    logit: 2.3891,
  },
  {
    id: 'mrk-pembrolizumab-combos-2026-07-06',
    date: '2026-07-06',
    company: 'Merck',
    ticker: 'MRK',
    drug: 'Pembrolizumab combos',
    indication: 'Lung Cancer (multiple trials)',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Oncology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9388,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_low_risk: 0.1065,
      ind_cancer: 0.2351,
    },
    totalAdj: 0.10520000010728836,
    logit: 2.7307,
  },
  {
    id: 'vera-atacicept-2026-07-07',
    date: '2026-07-07',
    company: 'Vera Therapeutics',
    ticker: 'VERA',
    drug: 'Atacicept',
    indication: 'IgA Nephropathy',
    type: 'PDUFA',
    appType: 'BLA',
    ta: 'Nephrology',
    phase: 'Phase 3',
    designations: ['Breakthrough Therapy', 'Orphan Drug'],
    enrollment: 376,
    nctId: 'NCT04716231',
    prob: 0.5238,
    tier: 'TIER_4',
    taRisk: 'HIGH_RISK',
    action: 'NO_POSITION',
    exit: 'N/A',
    runner: '0%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      BTD: 0.1505,
      orphan: 0.1454,
      ta_high_risk: -0.2834,
      novice_high_risk_ta: -0.4837,
    },
    totalAdj: -0.30979999899864197,
    logit: 0.0952,
  },
  {
    id: 'regn-mibavademab-2026-07-14',
    date: '2026-07-14',
    company: 'Regeneron',
    ticker: 'REGN',
    drug: 'Mibavademab',
    indication: 'Generalized Lipodystrophy',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Rare Disease',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.916,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
    },
    totalAdj: 0.08240000158548355,
    logit: 2.3891,
  },
  {
    id: 'azn-tezepelumab-2026-07-14',
    date: '2026-07-14',
    company: 'AstraZeneca',
    ticker: 'AZN',
    drug: 'Tezepelumab',
    indication: 'Eosinophilic Esophagitis',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'GI/Hepatology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.916,
    tier: 'TIER_1',
    taRisk: 'HIGH_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
    },
    totalAdj: 0.08240000158548355,
    logit: 2.3891,
  },
  {
    id: 'lly-lebrikizumab-2026-07-15',
    date: '2026-07-15',
    company: 'Eli Lilly',
    ticker: 'LLY',
    drug: 'Lebrikizumab',
    indication: 'Atopic Hand/Foot Dermatitis',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Dermatology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9238,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_low_risk: 0.1065,
    },
    totalAdj: 0.09019999951124191,
    logit: 2.4956,
  },
  {
    id: 'hrmy-pitolisant-2026-07-15',
    date: '2026-07-15',
    company: 'Harmony Biosciences',
    ticker: 'HRMY',
    drug: 'Pitolisant',
    indication: 'Prader-Willi Syndrome',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'CNS',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.5934,
    tier: 'TIER_4',
    taRisk: 'MOD_RISK',
    action: 'NO_POSITION',
    exit: 'N/A',
    runner: '0%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      ta_mod_risk: -0.1883,
    },
    totalAdj: -0.2401999980211258,
    logit: 0.378,
  },
  {
    id: 'lxrx-sotagliflozin-2026-07-15',
    date: '2026-07-15',
    company: 'Lexicon Pharmaceuticals',
    ticker: 'LXRX',
    drug: 'Sotagliflozin',
    indication: 'Hypertrophic Obstructive Cardiomyopathy',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Cardiovascular',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.5934,
    tier: 'TIER_4',
    taRisk: 'MOD_RISK',
    action: 'NO_POSITION',
    exit: 'N/A',
    runner: '0%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      ta_mod_risk: -0.1883,
    },
    totalAdj: -0.2401999980211258,
    logit: 0.378,
  },
  {
    id: 'rare-gtx-102-2026-07-15',
    date: '2026-07-15',
    company: 'Ultragenyx',
    ticker: 'RARE',
    drug: 'GTX-102',
    indication: 'Angelman Syndrome',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Rare Disease',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.6379,
    tier: 'TIER_3',
    taRisk: 'MOD_RISK',
    action: 'SMALL_POSITION_EARLY_EXIT',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
    },
    totalAdj: -0.195700004696846,
    logit: 0.5663,
  },
  {
    id: 'vrdn-vrdn-003-2026-07-15',
    date: '2026-07-15',
    company: 'Viridian Therapeutics',
    ticker: 'VRDN',
    drug: 'VRDN-003',
    indication: 'Thyroid Eye Disease',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Immunology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.6621,
    tier: 'TIER_3',
    taRisk: 'LOW_RISK',
    action: 'SMALL_POSITION_EARLY_EXIT',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      ta_low_risk: 0.1065,
    },
    totalAdj: -0.17149999737739563,
    logit: 0.6728,
  },
  {
    id: 'mrk-tulisokibart-2026-08-01',
    date: '2026-08-01',
    company: 'Merck',
    ticker: 'MRK',
    drug: 'Tulisokibart (IV+SC)',
    indication: 'Ulcerative Colitis',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'GI/Hepatology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.916,
    tier: 'TIER_1',
    taRisk: 'HIGH_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      experienced_sponsor: 0.7777,
    },
    totalAdj: 0.08240000158548355,
    logit: 2.3891,
  },
  {
    id: 'bmrn-vosoritide-2026-08-01',
    date: '2026-08-01',
    company: 'BioMarin',
    ticker: 'BMRN',
    drug: 'Vosoritide',
    indication: 'Hypochondroplasia',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Rare Disease',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.916,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      experienced_sponsor: 0.7777,
    },
    totalAdj: 0.08240000158548355,
    logit: 2.3891,
  },
  {
    id: 'dskyf-t-dxd-2026-08-03',
    date: '2026-08-03',
    company: 'Daiichi Sankyo',
    ticker: 'DSKYF',
    drug: 'T-DXd (trastuzumab deruxtecan)',
    indication: 'Advanced Cancer',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Oncology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9388,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_low_risk: 0.1065,
      ind_cancer: 0.2351,
    },
    totalAdj: 0.10520000010728836,
    logit: 2.7307,
  },
  {
    id: 'capr-cap-1002-2026-08-06',
    date: '2026-08-06',
    company: 'Capricor Therapeutics',
    ticker: 'CAPR',
    drug: 'CAP-1002 (deramiocel)',
    indication: 'Duchenne Muscular Dystrophy',
    type: 'PDUFA',
    appType: 'BLA',
    ta: 'Rare Disease',
    phase: 'Phase 3',
    designations: ['Orphan Drug', 'Rare Pediatric Disease'],
    enrollment: 106,
    nctId: 'NCT05126758',
    prob: 0.6708,
    tier: 'TIER_3',
    taRisk: 'MOD_RISK',
    action: 'SMALL_POSITION_EARLY_EXIT',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      orphan: 0.1454,
    },
    totalAdj: -0.16279999911785126,
    logit: 0.7118,
  },
  {
    id: 'private-177lu-edotreotide-2026-08-28',
    date: '2026-08-28',
    company: 'ITM Isotopen Technologien',
    ticker: 'Private',
    drug: '177Lu-edotreotide',
    indication: 'GEP Neuroendocrine Tumors',
    type: 'PDUFA',
    appType: 'NDA',
    ta: 'Oncology',
    phase: 'Phase 3',
    designations: ['Orphan Drug'],
    enrollment: 259,
    nctId: 'NCT04919226',
    prob: 0.7414,
    tier: 'TIER_2',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      orphan: 0.1454,
      ta_low_risk: 0.1065,
      ind_cancer: 0.2351,
    },
    totalAdj: -0.09220000356435776,
    logit: 1.0533,
  },
  {
    id: 'phar-besremi-2026-08-30',
    date: '2026-08-30',
    company: 'PharmaEssentia',
    ticker: 'PHAR',
    drug: 'Besremi (ropeginterferon alfa-2b)',
    indication: 'Essential Thrombocythemia',
    type: 'PDUFA',
    appType: 'sBLA',
    ta: 'Hematology',
    phase: 'Phase 2',
    designations: ['Orphan Drug'],
    enrollment: 91,
    nctId: 'NCT05482971',
    prob: 0.3886,
    tier: 'TIER_4',
    taRisk: 'HIGH_RISK',
    action: 'NO_POSITION',
    exit: 'N/A',
    runner: '0%',
    avoid: false,
    weekend: true,
    signals: {
      'sNDA/sBLA': -0.3978,
      inexperienced_sponsor: -1.045,
      orphan: 0.1454,
      ta_high_risk: -0.2834,
      novice_high_risk_ta: -0.4837,
    },
    totalAdj: -0.4449999928474426,
    logit: -0.4531,
  },
  {
    id: 'nvo-semaglutide-2026-09-01',
    date: '2026-09-01',
    company: 'Novo Nordisk',
    ticker: 'NVO',
    drug: 'Semaglutide',
    indication: 'Chronic Kidney Disease',
    type: 'Phase 2 Readout',
    appType: '',
    ta: 'Nephrology',
    phase: 'Phase 2',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.8915,
    tier: 'TIER_1',
    taRisk: 'HIGH_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_high_risk: -0.2834,
    },
    totalAdj: 0.05790000036358833,
    logit: 2.1057,
  },
  {
    id: 'nvo-awiqli-2026-09-01',
    date: '2026-09-01',
    company: 'Novo Nordisk',
    ticker: 'NVO',
    drug: 'Awiqli (insulin icodec)',
    indication: 'Type 2 Diabetes',
    type: 'PDUFA (Expected)',
    appType: 'NDA (resubmission)',
    ta: 'Metabolic',
    phase: 'Phase 3',
    designations: ['Resubmission fall 2025'],
    enrollment: 0,
    nctId: '',
    prob: 0.9003,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_mod_risk: -0.1883,
    },
    totalAdj: 0.06669999659061432,
    logit: 2.2008,
  },
  {
    id: 'amgn-dazodalibep-2026-09-02',
    date: '2026-09-02',
    company: 'Amgen',
    ticker: 'AMGN',
    drug: 'Dazodalibep',
    indication: 'Sjogren\'s Syndrome',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Immunology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9238,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_low_risk: 0.1065,
    },
    totalAdj: 0.09019999951124191,
    logit: 2.4956,
  },
  {
    id: 'nvo-ziltivekimab-2026-09-03',
    date: '2026-09-03',
    company: 'Novo Nordisk',
    ticker: 'NVO',
    drug: 'Ziltivekimab',
    indication: 'Cardiovascular/Heart Failure',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Cardiovascular',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9003,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_mod_risk: -0.1883,
    },
    totalAdj: 0.06669999659061432,
    logit: 2.2008,
  },
  {
    id: 'ucbjy-fenfluramine-2026-09-03',
    date: '2026-09-03',
    company: 'UCB',
    ticker: 'UCBJY',
    drug: 'Fenfluramine',
    indication: 'Dravet Syndrome',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'CNS',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9003,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_mod_risk: -0.1883,
    },
    totalAdj: 0.06669999659061432,
    logit: 2.2008,
  },
  {
    id: 'hluyy-eptinezumab-2026-09-05',
    date: '2026-09-05',
    company: 'Lundbeck',
    ticker: 'HLUYY',
    drug: 'Eptinezumab',
    indication: 'Chronic Migraine (Pediatric)',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'CNS',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.5459,
    tier: 'TIER_4',
    taRisk: 'MOD_RISK',
    action: 'NO_POSITION',
    exit: 'N/A',
    runner: '0%',
    avoid: false,
    weekend: true,
    signals: {
      pediatric: -0.194,
      inexperienced_sponsor: -1.045,
      ta_mod_risk: -0.1883,
    },
    totalAdj: -0.28769999742507935,
    logit: 0.184,
  },
  {
    id: 'nuvl-zidesamtinib-2026-09-18',
    date: '2026-09-18',
    company: 'Nuvalent',
    ticker: 'NUVL',
    drug: 'Zidesamtinib',
    indication: 'ROS1-positive NSCLC',
    type: 'PDUFA',
    appType: 'NDA',
    ta: 'Oncology',
    phase: 'Phase 1/2',
    designations: ['Breakthrough Therapy', 'Orphan Drug'],
    enrollment: 359,
    nctId: 'NCT05118789',
    prob: 0.7692,
    tier: 'TIER_2',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      BTD: 0.1505,
      orphan: 0.1454,
      ta_low_risk: 0.1065,
      ind_cancer: 0.2351,
    },
    totalAdj: -0.06440000236034393,
    logit: 1.2038,
  },
  {
    id: 'argx-efgartigimod-ph20-sc-2026-10-01',
    date: '2026-10-01',
    company: 'argenx',
    ticker: 'ARGX',
    drug: 'Efgartigimod PH20 SC',
    indication: 'Generalized Myasthenia Gravis',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Immunology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.6621,
    tier: 'TIER_3',
    taRisk: 'LOW_RISK',
    action: 'SMALL_POSITION_EARLY_EXIT',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      ta_low_risk: 0.1065,
    },
    totalAdj: -0.17149999737739563,
    logit: 0.6728,
  },
  {
    id: 'nvo-cagrisema-2026-10-01',
    date: '2026-10-01',
    company: 'Novo Nordisk',
    ticker: 'NVO',
    drug: 'CagriSema',
    indication: 'Obesity/Weight Management',
    type: 'PDUFA (Expected)',
    appType: 'NDA',
    ta: 'Metabolic',
    phase: 'Phase 3',
    designations: ['NDA filed Dec 2025', '10-month review expected'],
    enrollment: 0,
    nctId: '',
    prob: 0.9003,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_mod_risk: -0.1883,
    },
    totalAdj: 0.06669999659061432,
    logit: 2.2008,
  },
  {
    id: 'nvo-ziltivekimab-2026-10-05',
    date: '2026-10-05',
    company: 'Novo Nordisk',
    ticker: 'NVO',
    drug: 'Ziltivekimab',
    indication: 'Heart Failure',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Cardiovascular',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9003,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_mod_risk: -0.1883,
    },
    totalAdj: 0.06669999659061432,
    logit: 2.2008,
  },
  {
    id: 'azn-benralizumab-2026-10-06',
    date: '2026-10-06',
    company: 'AstraZeneca',
    ticker: 'AZN',
    drug: 'Benralizumab',
    indication: 'Eosinophilic Granulomatosis w/ Polyangiitis',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Immunology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9238,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_low_risk: 0.1065,
    },
    totalAdj: 0.09019999951124191,
    logit: 2.4956,
  },
  {
    id: 'incy-ruxolitinib-cream-2026-10-09',
    date: '2026-10-09',
    company: 'Incyte',
    ticker: 'INCY',
    drug: 'Ruxolitinib Cream',
    indication: 'Hidradenitis Suppurativa',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Dermatology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9238,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_low_risk: 0.1065,
    },
    totalAdj: 0.09019999951124191,
    logit: 2.4956,
  },
  {
    id: 'private-tabelecleucel-2026-10-10',
    date: '2026-10-10',
    company: 'Pierre Fabre',
    ticker: 'Private',
    drug: 'Tabelecleucel',
    indication: 'EBV+ Post-transplant Lymphoproliferative Disease',
    type: 'PDUFA',
    appType: 'BLA',
    ta: 'Oncology',
    phase: 'Phase 3',
    designations: ['Breakthrough Therapy', 'Orphan Drug'],
    enrollment: 115,
    nctId: 'NCT03394365',
    prob: 0.7249,
    tier: 'TIER_3',
    taRisk: 'LOW_RISK',
    action: 'SMALL_POSITION_EARLY_EXIT',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      inexperienced_sponsor: -1.045,
      BTD: 0.1505,
      orphan: 0.1454,
      ta_low_risk: 0.1065,
    },
    totalAdj: -0.10869999974966049,
    logit: 0.9688,
  },
  {
    id: 'ino-ino-3107-2026-10-30',
    date: '2026-10-30',
    company: 'INOVIO Pharmaceuticals',
    ticker: 'INO',
    drug: 'INO-3107',
    indication: 'Recurrent Respiratory Papillomatosis',
    type: 'PDUFA',
    appType: 'BLA',
    ta: 'Infectious',
    phase: 'Phase 1/2',
    designations: ['Breakthrough Therapy', 'Orphan Drug'],
    enrollment: 32,
    nctId: 'NCT04398433',
    prob: 0.7249,
    tier: 'TIER_3',
    taRisk: 'LOW_RISK',
    action: 'SMALL_POSITION_EARLY_EXIT',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      BTD: 0.1505,
      orphan: 0.1454,
      ta_low_risk: 0.1065,
    },
    totalAdj: -0.10869999974966049,
    logit: 0.9688,
  },
  {
    id: 'bmy-karxt-2026-11-01',
    date: '2026-11-01',
    company: 'Bristol-Myers Squibb',
    ticker: 'BMY',
    drug: 'KarXT (xanomeline-trospium)',
    indication: 'Bipolar-I Disorder',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'CNS',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9003,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      experienced_sponsor: 0.7777,
      ta_mod_risk: -0.1883,
    },
    totalAdj: 0.06669999659061432,
    logit: 2.2008,
  },
  {
    id: 'srrk-apitegromab-2026-11-01',
    date: '2026-11-01',
    company: 'Scholar Rock',
    ticker: 'SRRK',
    drug: 'Apitegromab',
    indication: 'Spinal Muscular Atrophy',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Rare Disease',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.6379,
    tier: 'TIER_3',
    taRisk: 'MOD_RISK',
    action: 'SMALL_POSITION_EARLY_EXIT',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      inexperienced_sponsor: -1.045,
    },
    totalAdj: -0.195700004696846,
    logit: 0.5663,
  },
  {
    id: 'smmt-ivonescimab-2026-11-14',
    date: '2026-11-14',
    company: 'Summit Therapeutics',
    ticker: 'SMMT',
    drug: 'Ivonescimab',
    indication: 'EGFR-mutated NSCLC (post-TKI)',
    type: 'PDUFA',
    appType: 'BLA',
    ta: 'Oncology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: 'TBD',
    prob: 0.7126,
    tier: 'TIER_3',
    taRisk: 'LOW_RISK',
    action: 'SMALL_POSITION_EARLY_EXIT',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: true,
    signals: {
      inexperienced_sponsor: -1.045,
      ta_low_risk: 0.1065,
      ind_cancer: 0.2351,
    },
    totalAdj: -0.12099999934434891,
    logit: 0.9079,
  },
  {
    id: 'sny-itepekimab-2026-12-01',
    date: '2026-12-01',
    company: 'Sanofi',
    ticker: 'SNY',
    drug: 'Itepekimab',
    indication: 'COPD',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Respiratory',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.916,
    tier: 'TIER_1',
    taRisk: 'MOD_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
    },
    totalAdj: 0.08240000158548355,
    logit: 2.3891,
  },
  {
    id: 'argx-efgartigimod-ph20-sc-2026-12-01',
    date: '2026-12-01',
    company: 'argenx',
    ticker: 'ARGX',
    drug: 'Efgartigimod PH20 SC',
    indication: 'Inflammatory Myopathy',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Immunology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.6621,
    tier: 'TIER_3',
    taRisk: 'LOW_RISK',
    action: 'SMALL_POSITION_EARLY_EXIT',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      inexperienced_sponsor: -1.045,
      ta_low_risk: 0.1065,
    },
    totalAdj: -0.17149999737739563,
    logit: 0.6728,
  },
  {
    id: 'sny-pcv21-2026-12-01',
    date: '2026-12-01',
    company: 'Sanofi',
    ticker: 'SNY',
    drug: 'PCV21',
    indication: 'Pneumococcal Infections',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Vaccines',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.916,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
    },
    totalAdj: 0.08240000158548355,
    logit: 2.3891,
  },
  {
    id: 'jnj-icotrokinra-2026-12-01',
    date: '2026-12-01',
    company: 'Johnson & Johnson',
    ticker: 'JNJ',
    drug: 'Icotrokinra',
    indication: 'Psoriasis / IBD (oral IL-23)',
    type: 'PDUFA (Expected)',
    appType: 'NDA',
    ta: 'Immunology',
    phase: 'Phase 3',
    designations: ['First oral IL-23 blocker'],
    enrollment: 0,
    nctId: '',
    prob: 0.9238,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_low_risk: 0.1065,
    },
    totalAdj: 0.09019999951124191,
    logit: 2.4956,
  },
  {
    id: 'pfe-pf-06821497-2026-12-02',
    date: '2026-12-02',
    company: 'Pfizer',
    ticker: 'PFE',
    drug: 'PF-06821497 (mevrometostat)',
    indication: 'mCRPC',
    type: 'Phase 3 Readout',
    appType: '',
    ta: 'Oncology',
    phase: 'Phase 3',
    designations: [],
    enrollment: 0,
    nctId: '',
    prob: 0.9238,
    tier: 'TIER_1',
    taRisk: 'LOW_RISK',
    action: 'STANDARD_POSITION',
    exit: 'T-5 to T-7',
    runner: '20%',
    avoid: false,
    weekend: false,
    signals: {
      experienced_sponsor: 0.7777,
      ta_low_risk: 0.1065,
    },
    totalAdj: 0.09019999951124191,
    logit: 2.4956,
  },
];

// ═══════════════════════════════════════════════════
// HISTORICAL APPROVAL RATES BY THERAPEUTIC AREA
// Source: 486-event backtest (2018-2025)
// ═══════════════════════════════════════════════════
const HIST_APPROVAL_RATES = {
  "Oncology": {
    "approved": 68,
    "total": 78,
    "rate": 87.2
  },
  "Immunology": {
    "approved": 22,
    "total": 25,
    "rate": 88.0
  },
  "Infectious Disease": {
    "approved": 41,
    "total": 45,
    "rate": 91.1
  },
  "Dermatology": {
    "approved": 18,
    "total": 20,
    "rate": 90.0
  },
  "Vaccines": {
    "approved": 12,
    "total": 13,
    "rate": 92.3
  },
  "Respiratory": {
    "approved": 15,
    "total": 17,
    "rate": 88.2
  },
  "CNS": {
    "approved": 38,
    "total": 52,
    "rate": 73.1
  },
  "Cardiovascular": {
    "approved": 19,
    "total": 24,
    "rate": 79.2
  },
  "Metabolic": {
    "approved": 24,
    "total": 31,
    "rate": 77.4
  },
  "Rare Disease": {
    "approved": 45,
    "total": 55,
    "rate": 81.8
  },
  "Hematology": {
    "approved": 28,
    "total": 34,
    "rate": 82.4
  },
  "Ophthalmology": {
    "approved": 9,
    "total": 13,
    "rate": 69.2
  },
  "GI/Hepatology": {
    "approved": 12,
    "total": 16,
    "rate": 75.0
  },
  "Nephrology": {
    "approved": 6,
    "total": 9,
    "rate": 66.7
  },
  "Musculoskeletal": {
    "approved": 8,
    "total": 11,
    "rate": 72.7
  },
  "Women's Health": {
    "approved": 5,
    "total": 6,
    "rate": 83.3
  },
  "Pain Management": {
    "approved": 3,
    "total": 7,
    "rate": 42.9
  }
};

// ═══════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════
const getTierColor = (tier) => {
  const colors = {
    TIER_1: '#22c55e',
    TIER_2: '#eab308',
    TIER_3: '#f97316',
    TIER_4: '#ef4444',
  };
  return colors[tier] || '#6b7280';
};

const getTierBgClass = (tier) => {
  const classes = {
    TIER_1: 'bg-green-950 text-green-400 border border-green-700',
    TIER_2: 'bg-yellow-950 text-yellow-400 border border-yellow-700',
    TIER_3: 'bg-orange-950 text-orange-400 border border-orange-700',
    TIER_4: 'bg-red-950 text-red-400 border border-red-700',
  };
  return classes[tier] || 'bg-gray-800 text-gray-400 border border-gray-700';
};

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
};

const fmtProb = (p) => (p * 100).toFixed(1);

const fmtMoney = (n) => {
  if (!n && n !== 0) return 'N/A';
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
};

const getSentimentColor = (score) => {
  if (score >= 80) return '#22c55e';
  if (score >= 60) return '#eab308';
  if (score >= 40) return '#f97316';
  return '#ef4444';
};

const getRunwayColor = (months) => {
  if (!months) return '#6b7280';
  if (months >= 24) return '#22c55e';
  if (months >= 12) return '#eab308';
  if (months >= 6) return '#f97316';
  return '#ef4444';
};

// ═══════════════════════════════════════════════════
// CUSTOM HOOKS — Market Data & Sentiment
// ═══════════════════════════════════════════════════
const useMarketData = (ticker) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const cache = useRef({});

  useEffect(() => {
    if (!ticker || ticker === 'Private') return;

    // Check cache (5 min TTL)
    const cached = cache.current[ticker];
    if (cached && Date.now() - cached.ts < 300000) {
      setData(cached.data);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [quoteRes, financialsRes, insiderRes] = await Promise.allSettled([
          fetch(`/api/market-data?ticker=${ticker}&type=quote`),
          fetch(`/api/market-data?ticker=${ticker}&type=financials`),
          fetch(`/api/market-data?ticker=${ticker}&type=insider`),
        ]);

        const result = {};
        if (quoteRes.status === 'fulfilled' && quoteRes.value.ok) {
          result.quote = await quoteRes.value.json();
        }
        if (financialsRes.status === 'fulfilled' && financialsRes.value.ok) {
          result.financials = await financialsRes.value.json();
        }
        if (insiderRes.status === 'fulfilled' && insiderRes.value.ok) {
          result.insider = await insiderRes.value.json();
        }

        cache.current[ticker] = { data: result, ts: Date.now() };
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [ticker]);

  return { data, loading, error };
};

const useSentiment = (ticker) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const cache = useRef({});

  useEffect(() => {
    if (!ticker || ticker === 'Private') return;

    const cached = cache.current[ticker];
    if (cached && Date.now() - cached.ts < 900000) {
      setData(cached.data);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/sentiment?ticker=${ticker}`);
        if (res.ok) {
          const result = await res.json();
          cache.current[ticker] = { data: result, ts: Date.now() };
          setData(result);
        }
      } catch (err) {
        // Silently fail for sentiment
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [ticker]);

  return { data, loading };
};

// ═══════════════════════════════════════════════════
// COMPONENTS
// ═══════════════════════════════════════════════════

const CountdownTimer = ({ targetDate }) => {
  const [countdown, setCountdown] = useState({
    days: 0, hours: 0, minutes: 0, seconds: 0, expired: false,
  });

  useEffect(() => {
    const updateCountdown = () => {
      const now = new Date().getTime();
      const target = new Date(targetDate).getTime();
      const distance = target - now;
      if (distance < 0) {
        setCountdown({ days: 0, hours: 0, minutes: 0, seconds: 0, expired: true });
        return;
      }
      setCountdown({
        days: Math.floor(distance / (1000 * 60 * 60 * 24)),
        hours: Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
        minutes: Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60)),
        seconds: Math.floor((distance % (1000 * 60)) / 1000),
        expired: false,
      });
    };
    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [targetDate]);

  if (countdown.expired) {
    return <div className="text-yellow-400 font-mono text-sm font-bold animate-pulse">DECISION PENDING</div>;
  }

  return (
    <div className="flex gap-2 items-center font-mono text-sm tabular-nums">
      {[
        { val: countdown.days, label: 'days' },
        { val: String(countdown.hours).padStart(2, '0'), label: 'hrs' },
        { val: String(countdown.minutes).padStart(2, '0'), label: 'min' },
        { val: String(countdown.seconds).padStart(2, '0'), label: 'sec' },
      ].map((item, i) => (
        <React.Fragment key={item.label}>
          {i > 0 && <span className="text-gray-500">:</span>}
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400">{item.val}</div>
            <div className="text-xs text-gray-400">{item.label}</div>
          </div>
        </React.Fragment>
      ))}
    </div>
  );
};

// ── Catalyst Card ──────────────────────────────────
const CatalystCard = ({ catalyst, onExpand }) => {
  const daysUntil = Math.ceil((new Date(catalyst.date) - new Date()) / (1000 * 60 * 60 * 24));
  const isImminent = daysUntil <= 7 && daysUntil >= 0;
  const isPast = daysUntil < 0;

  return (
    <div
      onClick={() => onExpand(catalyst)}
      className={`bg-gray-900 border p-4 cursor-pointer hover:border-blue-500 hover:bg-gray-800 transition-all rounded-none ${
        isImminent ? 'border-yellow-600 ring-1 ring-yellow-600/30' : isPast ? 'border-gray-800 opacity-60' : 'border-gray-700'
      }`}
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-400">{formatDate(catalyst.date)}</span>
            {isImminent && !isPast && (
              <span className="text-xs bg-yellow-900 text-yellow-300 px-1.5 py-0.5 font-mono border border-yellow-700 animate-pulse">
                {daysUntil === 0 ? 'TODAY' : `${daysUntil}d`}
              </span>
            )}
          </div>
          <div className="flex gap-2 items-baseline">
            <span className="font-bold text-white text-lg">{catalyst.ticker}</span>
            <span className="text-sm text-gray-400 truncate">{catalyst.drug}</span>
          </div>
        </div>
      </div>
      <div className="flex justify-between items-end">
        <div>
          <div className="text-xs text-gray-500 mb-1">Approval Prob.</div>
          <div className="text-2xl font-bold tabular-nums font-mono" style={{ color: getTierColor(catalyst.tier) }}>
            {fmtProb(catalyst.prob)}%
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className={`px-3 py-1 text-xs font-mono font-bold rounded-none ${getTierBgClass(catalyst.tier)}`}>
            {catalyst.tier.replace('_', ' ')}
          </div>
          {catalyst.designations.length > 0 && (
            <div className="flex gap-1 flex-wrap justify-end">
              {catalyst.designations.slice(0, 2).map((d) => (
                <span key={d} className="text-xs text-blue-400 bg-blue-950 px-1 border border-blue-800 font-mono">
                  {d.replace('Breakthrough Therapy', 'BTD').replace('Priority Review', 'PR').replace('Orphan Drug', 'OD').replace('Fast Track', 'FT').replace('Accelerated Approval', 'AA')}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="text-xs text-gray-500 mt-3 truncate">{catalyst.indication}</div>
      <div className="flex gap-2 mt-2">
        {catalyst.weekend && (
          <span className="text-xs text-red-400 flex items-center gap-1">
            <AlertTriangle size={10} /> Weekend
          </span>
        )}
        {catalyst.taRisk === 'HIGH_RISK' && (
          <span className="text-xs text-red-400 flex items-center gap-1">
            <Flame size={10} /> High TA Risk
          </span>
        )}
      </div>
    </div>
  );
};

// ── Detail Modal (Enhanced with tabs) ──────────────
const DetailModal = ({ catalyst, onClose }) => {
  const [activeDetailTab, setActiveDetailTab] = useState('overview');
  const { data: marketData, loading: marketLoading } = useMarketData(catalyst?.ticker);
  const { data: sentimentData, loading: sentimentLoading } = useSentiment(catalyst?.ticker);

  if (!catalyst) return null;

  const quote = marketData?.quote || {};
  const financials = marketData?.financials || {};
  const insiderTrades = Array.isArray(marketData?.insider) ? marketData.insider : [];
  const cashRunway = financials?.cashRunway || {};

  // Parse LunarCrush sentiment data
  const lcData = sentimentData?.data || {};
  const hasSentiment = !!(lcData.interactions_24h || lcData.num_posts);

  const histRate = HIST_APPROVAL_RATES[catalyst.ta] || null;

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-start justify-center pt-4 sm:pt-8 overflow-y-auto p-2 sm:p-0" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 w-full max-w-3xl mx-auto mb-8" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="border-b border-gray-700 p-4 sm:p-6 flex justify-between items-start">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h2 className="text-xl sm:text-2xl font-bold text-white">{catalyst.drug}</h2>
              <div className={`px-3 py-1 text-xs font-mono font-bold rounded-none ${getTierBgClass(catalyst.tier)}`}>
                {catalyst.tier.replace('_', ' ')}
              </div>
            </div>
            <p className="text-sm text-gray-400">
              {catalyst.company} ({catalyst.ticker}) &middot; {formatDate(catalyst.date)}
            </p>
            {/* Live price if available */}
            {quote.price && (
              <div className="flex items-center gap-3 mt-2">
                <span className="text-lg font-bold font-mono text-white">${quote.price?.toFixed(2)}</span>
                <span className={`text-sm font-mono flex items-center gap-1 ${
                  quote.changesPercentage >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {quote.changesPercentage >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                  {quote.changesPercentage?.toFixed(2)}%
                </span>
                {quote.volume && (
                  <span className="text-xs text-gray-500 font-mono">Vol: {fmtMoney(quote.volume)}</span>
                )}
              </div>
            )}
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition p-1">
            <X size={24} />
          </button>
        </div>

        {/* Tab Bar */}
        <div className="border-b border-gray-700 flex overflow-x-auto">
          {[
            { id: 'overview', label: 'Overview', icon: Eye },
            { id: 'signals', label: 'Signals', icon: Zap },
            { id: 'market', label: 'Market', icon: TrendingUp },
            { id: 'insider', label: 'Insider', icon: Users },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveDetailTab(tab.id)}
                className={`px-4 py-3 text-xs font-mono uppercase border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${
                  activeDetailTab === tab.id
                    ? 'border-blue-400 text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}
              >
                <Icon size={12} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="p-4 sm:p-6 space-y-6">
          {activeDetailTab === 'overview' && (
            <>
              {/* Key Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: 'INDICATION', value: catalyst.indication },
                  { label: 'PHASE', value: catalyst.phase },
                  { label: 'TYPE', value: `${catalyst.type} (${catalyst.appType})` },
                  { label: 'THERAPEUTIC AREA', value: catalyst.ta },
                ].map((item) => (
                  <div key={item.label} className="bg-gray-800 p-3 border border-gray-700">
                    <div className="text-xs text-gray-500 mb-1">{item.label}</div>
                    <div className="text-sm text-white">{item.value}</div>
                  </div>
                ))}
              </div>

              {/* ODIN Probability */}
              <div>
                <div className="text-xs text-gray-500 mb-3 font-mono">ODIN v10.66 PROBABILITY</div>
                <div className="flex items-center gap-6">
                  <div className="text-5xl font-bold tabular-nums font-mono" style={{ color: getTierColor(catalyst.tier) }}>
                    {fmtProb(catalyst.prob)}%
                  </div>
                  <div className="flex-1">
                    <div className="w-full bg-gray-800 border border-gray-700 h-6 relative overflow-hidden">
                      <div
                        className="h-full transition-all duration-700"
                        style={{ width: `${catalyst.prob * 100}%`, backgroundColor: getTierColor(catalyst.tier), opacity: 0.7 }}
                      />
                      <div className="absolute inset-0 flex items-center px-2">
                        <span className="text-xs font-mono text-gray-300">BASE 83.4%</span>
                        <div className="flex-1" />
                        <span className="text-xs font-mono" style={{ color: getTierColor(catalyst.tier) }}>
                          {catalyst.totalAdj > 0 ? '+' : ''}{fmtProb(catalyst.totalAdj)} adj
                        </span>
                      </div>
                    </div>
                    <div className="flex justify-between mt-1 text-xs text-gray-600 font-mono">
                      <span>0%</span><span>50%</span><span>100%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Historical TA Rate */}
              {histRate && (
                <div className="bg-gray-800 border border-gray-700 p-4">
                  <div className="text-xs text-gray-500 mb-2 font-mono">HISTORICAL {catalyst.ta.toUpperCase()} APPROVAL RATE</div>
                  <div className="flex items-center gap-4">
                    <div className="text-2xl font-bold font-mono" style={{ color: histRate.rate >= 80 ? '#22c55e' : histRate.rate >= 70 ? '#eab308' : '#f97316' }}>
                      {histRate.rate.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-400">
                      {histRate.approved} approved / {histRate.total} total (2018-2025)
                    </div>
                    <div className="flex-1">
                      <div className="w-full bg-gray-700 h-2 overflow-hidden">
                        <div className="h-full bg-blue-500 transition-all" style={{ width: `${histRate.rate}%` }} />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Designations */}
              {catalyst.designations.length > 0 && (
                <div>
                  <div className="text-xs text-gray-500 mb-3 font-mono">DESIGNATIONS</div>
                  <div className="flex flex-wrap gap-2">
                    {catalyst.designations.map((des) => (
                      <div key={des} className="bg-blue-950 text-blue-300 text-xs px-3 py-1.5 border border-blue-700 font-mono">
                        {des}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Trading Rec */}
              <div>
                <div className="text-xs text-gray-500 mb-3 font-mono">TRADING RECOMMENDATION</div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="bg-gray-800 p-3 border border-gray-700">
                    <span className="text-xs text-gray-500 block mb-1">Action</span>
                    <span className="text-white font-mono text-xs">{catalyst.action.replace(/_/g, ' ')}</span>
                  </div>
                  <div className="bg-gray-800 p-3 border border-gray-700">
                    <span className="text-xs text-gray-500 block mb-1">Exit</span>
                    <span className="text-white font-mono text-xs">{catalyst.exit}</span>
                  </div>
                  <div className="bg-gray-800 p-3 border border-gray-700">
                    <span className="text-xs text-gray-500 block mb-1">Runner</span>
                    <span className="text-white font-mono text-xs">{catalyst.runner}</span>
                  </div>
                </div>
              </div>

              {/* Warnings */}
              {catalyst.weekend && (
                <div className="bg-red-950 border border-red-700 p-3 flex gap-2">
                  <AlertTriangle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-red-300">Weekend PDUFA — decision may come Friday after hours or over the weekend</span>
                </div>
              )}

              {/* Links */}
              {catalyst.nctId && (
                <div className="flex gap-2 pt-4 border-t border-gray-700">
                  <a href={`https://clinicaltrials.gov/ct2/show/${catalyst.nctId}`} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm">
                    <ExternalLink size={16} /> ClinicalTrials.gov
                  </a>
                </div>
              )}
            </>
          )}

          {activeDetailTab === 'signals' && (
            <div>
              <div className="text-xs text-gray-500 mb-3 font-mono">ODIN v10.66 SIGNAL DECOMPOSITION</div>
              <div className="space-y-2 text-xs font-mono">
                {Object.entries(catalyst.signals).map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center p-2 bg-gray-800 border border-gray-700">
                    <span className="text-gray-300">{key.replace(/_/g, ' ')}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-700 h-2 overflow-hidden">
                        <div
                          className={`h-full ${value > 0 ? 'bg-green-500' : 'bg-red-500'}`}
                          style={{ width: `${Math.min(Math.abs(value) * 100, 100)}%`, marginLeft: value < 0 ? 'auto' : 0 }}
                        />
                      </div>
                      <span className={`w-16 text-right ${value > 0 ? 'text-green-400' : value < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                        {value > 0 ? '+' : ''}{(value * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
                <div className="flex justify-between pt-3 border-t border-gray-600 text-sm">
                  <span className="text-gray-200 font-bold">Total Adjustment</span>
                  <span className={catalyst.totalAdj > 0 ? 'text-green-400' : catalyst.totalAdj < 0 ? 'text-red-400' : 'text-gray-400'}>
                    {catalyst.totalAdj > 0 ? '+' : ''}{(catalyst.totalAdj * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-200 font-bold">Raw Logit</span>
                  <span className="text-blue-400">{catalyst.logit?.toFixed(4)}</span>
                </div>
              </div>
            </div>
          )}

          {activeDetailTab === 'market' && (
            <div className="space-y-6">
              {marketLoading && (
                <div className="flex items-center justify-center py-12 gap-2 text-gray-400">
                  <Loader size={16} className="animate-spin" /> Loading market data...
                </div>
              )}

              {!marketLoading && !quote.price && (
                <div className="bg-gray-800 border border-gray-700 p-6 text-center">
                  <DollarSign size={24} className="text-gray-500 mx-auto mb-2" />
                  <div className="text-sm text-gray-400 mb-1">Market data unavailable</div>
                  <div className="text-xs text-gray-500">
                    {catalyst.ticker === 'Private' ? 'Private company — no public market data' : 'Unable to retrieve quote data for this ticker.'}
                  </div>
                </div>
              )}

              {quote.price && (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                      { label: 'PRICE', value: `$${quote.price?.toFixed(2)}`, color: 'text-white' },
                      { label: 'CHANGE', value: `${quote.changesPercentage >= 0 ? '+' : ''}${quote.changesPercentage?.toFixed(2)}%`, color: quote.changesPercentage >= 0 ? 'text-green-400' : 'text-red-400' },
                      { label: 'MKT CAP', value: fmtMoney(quote.marketCap), color: 'text-blue-400' },
                      { label: 'VOLUME', value: fmtMoney(quote.volume), color: 'text-gray-300' },
                    ].map((item) => (
                      <div key={item.label} className="bg-gray-800 p-3 border border-gray-700">
                        <div className="text-xs text-gray-500 mb-1 font-mono">{item.label}</div>
                        <div className={`text-lg font-bold font-mono ${item.color}`}>{item.value}</div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Cash Runway */}
              {cashRunway.cash > 0 && (
                <div className="bg-gray-800 border border-gray-700 p-4">
                  <div className="text-xs text-gray-500 mb-3 font-mono">CASH RUNWAY (Desperation Index)</div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Cash</div>
                      <div className="text-lg font-bold text-white font-mono">{fmtMoney(cashRunway.cash)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Quarterly Burn</div>
                      <div className="text-lg font-bold text-red-400 font-mono">{fmtMoney(cashRunway.quarterlyBurn)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Runway</div>
                      <div className="text-lg font-bold font-mono" style={{ color: getRunwayColor(cashRunway.runwayMonths) }}>
                        {cashRunway.runwayMonths ? `${cashRunway.runwayMonths.toFixed(0)} mo` : 'N/A'}
                      </div>
                    </div>
                  </div>
                  {cashRunway.runwayMonths && cashRunway.runwayMonths < 12 && (
                    <div className="mt-3 text-xs text-red-400 flex items-center gap-1">
                      <AlertTriangle size={12} /> Low runway — company may need to raise capital
                    </div>
                  )}
                </div>
              )}

              {/* Social Sentiment (LunarCrush) */}
              {sentimentLoading && (
                <div className="flex items-center justify-center py-6 gap-2 text-gray-400 text-xs">
                  <Loader size={14} className="animate-spin" /> Loading sentiment...
                </div>
              )}
              {!sentimentLoading && hasSentiment && (
                <div className="bg-gray-800 border border-gray-700 p-4">
                  <div className="text-xs text-gray-500 mb-3 font-mono flex items-center gap-2">
                    SOCIAL SENTIMENT
                    {lcData.trend && (
                      <span className={`px-1.5 py-0.5 text-[10px] ${lcData.trend === 'up' ? 'bg-green-500/20 text-green-400' : lcData.trend === 'down' ? 'bg-red-500/20 text-red-400' : 'bg-gray-500/20 text-gray-400'}`}>
                        {lcData.trend === 'up' ? '▲ TRENDING UP' : lcData.trend === 'down' ? '▼ TRENDING DOWN' : '─ FLAT'}
                      </span>
                    )}
                    <span className="text-gray-600 ml-auto">via LunarCrush</span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 mb-3">
                    <div>
                      <div className="text-xs text-gray-500 mb-1">24h Engagements</div>
                      <div className="text-lg font-bold text-blue-400 font-mono">{fmtMoney(lcData.interactions_24h || 0)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Mentions</div>
                      <div className="text-lg font-bold text-white font-mono">{lcData.num_posts || 0}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Creators</div>
                      <div className="text-lg font-bold text-purple-400 font-mono">{lcData.num_contributors || 0}</div>
                    </div>
                  </div>
                  {/* Platform sentiment breakdown */}
                  {lcData.types_sentiment && (
                    <div className="space-y-1.5">
                      <div className="text-[10px] text-gray-500 font-mono">SENTIMENT BY PLATFORM</div>
                      {Object.entries(lcData.types_sentiment)
                        .filter(([, val]) => val !== undefined && val !== null)
                        .map(([platform, score]) => {
                          const count = lcData.types_count?.[platform] || 0;
                          const interactions = lcData.types_interactions?.[platform] || 0;
                          const pName = platform.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase()).replace('Reddit Post', 'Reddit').replace('Tiktok Video', 'TikTok').replace('Youtube Video', 'YouTube').replace('Tweet', 'X/Twitter');
                          return (
                            <div key={platform} className="flex items-center gap-2 text-xs">
                              <span className="text-gray-400 w-20 truncate font-mono">{pName}</span>
                              <div className="flex-1 bg-gray-700 h-1.5">
                                <div
                                  className={`h-full ${score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                  style={{ width: `${Math.min(score, 100)}%` }}
                                />
                              </div>
                              <span className={`font-mono text-xs w-8 text-right ${score >= 70 ? 'text-green-400' : score >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                                {score}%
                              </span>
                              <span className="text-gray-600 text-[10px] w-16 text-right font-mono">{count} posts</span>
                            </div>
                          );
                        })}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeDetailTab === 'insider' && (
            <div className="space-y-4">
              {marketLoading && (
                <div className="flex items-center justify-center py-12 gap-2 text-gray-400">
                  <Loader size={16} className="animate-spin" /> Loading insider data...
                </div>
              )}

              {!marketLoading && insiderTrades.length === 0 && (
                <div className="bg-gray-800 border border-gray-700 p-6 text-center">
                  <Users size={24} className="text-gray-500 mx-auto mb-2" />
                  <div className="text-sm text-gray-400 mb-1">No recent insider transactions</div>
                  <div className="text-xs text-gray-500">
                    No SEC Section 16 filings found for {catalyst.ticker}. This can mean no insider buying/selling activity in the reporting period, or the data is unavailable for this ticker.
                  </div>
                </div>
              )}

              {insiderTrades.length > 0 && (
                <>
                  <div className="text-xs text-gray-500 font-mono mb-2">RECENT INSIDER TRANSACTIONS (SEC Section 16)</div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono">
                      <thead>
                        <tr className="border-b border-gray-700 bg-gray-800">
                          <th className="px-3 py-2 text-left text-gray-400">Date</th>
                          <th className="px-3 py-2 text-left text-gray-400">Name</th>
                          <th className="px-3 py-2 text-left text-gray-400">Type</th>
                          <th className="px-3 py-2 text-right text-gray-400">Shares</th>
                          <th className="px-3 py-2 text-right text-gray-400">Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {insiderTrades.slice(0, 10).map((trade, i) => (
                          <tr key={i} className="border-b border-gray-800">
                            <td className="px-3 py-2 text-gray-300">{trade.transactionDate}</td>
                            <td className="px-3 py-2 text-gray-300 truncate max-w-32">{trade.reportingName}</td>
                            <td className={`px-3 py-2 ${
                              trade.transactionType === 'P-Purchase' ? 'text-green-400' : 'text-red-400'
                            }`}>
                              {trade.transactionType === 'P-Purchase' ? 'BUY' : 'SELL'}
                            </td>
                            <td className="px-3 py-2 text-right text-gray-300">{trade.securitiesTransacted?.toLocaleString()}</td>
                            <td className="px-3 py-2 text-right text-gray-300">${trade.price?.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {(() => {
                    const buys = insiderTrades.filter(t => t.transactionType === 'P-Purchase').length;
                    const sells = insiderTrades.filter(t => t.transactionType !== 'P-Purchase').length;
                    return (
                      <div className="flex gap-4 text-xs font-mono">
                        <span className="text-green-400">Buys: {buys}</span>
                        <span className="text-red-400">Sells: {sells}</span>
                        <span className={buys > sells ? 'text-green-400' : buys < sells ? 'text-red-400' : 'text-gray-400'}>
                          Signal: {buys > sells ? 'BULLISH' : buys < sells ? 'BEARISH' : 'NEUTRAL'}
                        </span>
                      </div>
                    );
                  })()}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Dashboard View ─────────────────────────────────
const DashboardView = ({ catalysts, onExpandCatalyst, onNavigate }) => {
  const nextCatalyst = catalysts[0];
  const tier1Count = catalysts.filter((c) => c.tier === 'TIER_1').length;
  const tier2Count = catalysts.filter((c) => c.tier === 'TIER_2').length;
  const avgProb = (catalysts.reduce((sum, c) => sum + c.prob, 0) / catalysts.length * 100).toFixed(1);
  const weekendCount = catalysts.filter(c => c.weekend).length;

  // Next 30 days catalysts
  const now = new Date();
  const next30 = catalysts.filter(c => {
    const d = new Date(c.date);
    const diff = (d - now) / (1000 * 60 * 60 * 24);
    return diff >= 0 && diff <= 30;
  });

  // Next 7 days (imminent)
  const next7 = catalysts.filter(c => {
    const d = new Date(c.date);
    const diff = (d - now) / (1000 * 60 * 60 * 24);
    return diff >= 0 && diff <= 7;
  });

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <div className="text-center py-4 sm:py-8">
        <h2 className="text-3xl sm:text-5xl font-bold font-mono tracking-tight mb-3">
          FDA Catalyst <span className="text-blue-400">Intelligence</span>
        </h2>
        <p className="text-gray-400 text-sm sm:text-base max-w-2xl mx-auto mb-6">
          Machine-learning approval probability scores for upcoming PDUFA dates.
          Powered by ODIN v10.66 — trained on 486 historical FDA decisions.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <button onClick={() => onNavigate('screener')}
            className="bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 text-sm font-mono transition flex items-center gap-2">
            <BarChart3 size={14} /> Full Screener <ChevronRight size={14} />
          </button>
          <button onClick={() => onNavigate('calendar')}
            className="bg-gray-800 hover:bg-gray-700 text-gray-200 px-5 py-2.5 text-sm font-mono border border-gray-700 transition flex items-center gap-2">
            <Calendar size={14} /> PDUFA Calendar
          </button>
        </div>
      </div>

      {/* Key Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        {[
          { label: 'ACTIVE CATALYSTS', value: catalysts.length, color: 'text-white', icon: Target },
          { label: 'HIGH CONVICTION', value: `${tier1Count + tier2Count}`, sub: `${tier1Count} T1 · ${tier2Count} T2`, color: 'text-green-400', icon: Shield },
          { label: 'AVG PROBABILITY', value: `${avgProb}%`, color: 'text-yellow-400', icon: Brain },
          { label: 'NEXT 7 DAYS', value: next7.length, sub: next7.length > 0 ? `Next: ${next7[0].ticker}` : 'None imminent', color: next7.length > 0 ? 'text-orange-400' : 'text-gray-500', icon: Flame },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-gray-900 border border-gray-700 p-3 sm:p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <Icon size={12} className="text-gray-500" />
                <div className="text-[10px] sm:text-xs text-gray-400 font-mono">{stat.label}</div>
              </div>
              <div className={`text-2xl sm:text-3xl font-bold tabular-nums font-mono ${stat.color}`}>{stat.value}</div>
              {stat.sub && <div className="text-[10px] text-gray-500 font-mono mt-1">{stat.sub}</div>}
            </div>
          );
        })}
      </div>

      {/* Next Catalyst Spotlight */}
      <div className="bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800 border border-gray-700 p-4 sm:p-6 cursor-pointer hover:border-blue-500 transition"
        onClick={() => onExpandCatalyst(nextCatalyst)}>
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center gap-2">
            <Zap size={14} className="text-blue-400" />
            <h3 className="text-xs text-gray-400 font-mono uppercase">NEXT CATALYST EVENT</h3>
          </div>
          <div className={`px-3 py-1 text-xs font-mono font-bold ${getTierBgClass(nextCatalyst.tier)}`}>
            {nextCatalyst.tier.replace('_', ' ')}
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6 mb-6">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2">{nextCatalyst.drug}</h2>
            <p className="text-gray-400">{nextCatalyst.company} ({nextCatalyst.ticker})</p>
            <p className="text-sm text-gray-500 mt-1">{nextCatalyst.indication}</p>
            {nextCatalyst.designations.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {nextCatalyst.designations.map((d) => (
                  <span key={d} className="text-xs text-blue-400 bg-blue-950 px-2 py-0.5 border border-blue-800 font-mono">{d}</span>
                ))}
              </div>
            )}
          </div>
          <div className="flex flex-col justify-between">
            <div>
              <div className="text-4xl sm:text-5xl font-bold tabular-nums font-mono" style={{ color: getTierColor(nextCatalyst.tier) }}>
                {fmtProb(nextCatalyst.prob)}%
              </div>
              <div className="text-gray-400 text-sm mt-1">ODIN Approval Probability</div>
            </div>
          </div>
        </div>
        <div className="border-t border-gray-700 pt-4">
          <div className="text-xs text-gray-500 mb-2 font-mono">COUNTDOWN TO DECISION</div>
          <CountdownTimer targetDate={nextCatalyst.date} />
        </div>
      </div>

      {/* Tier Distribution */}
      <div className="bg-gray-900 border border-gray-700 p-4">
        <div className="text-xs text-gray-400 mb-3 font-mono">TIER DISTRIBUTION</div>
        <div className="flex h-8 w-full overflow-hidden">
          {['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4'].map((tier) => {
            const count = catalysts.filter((c) => c.tier === tier).length;
            const pct = (count / catalysts.length) * 100;
            return (
              <div key={tier} style={{ width: `${pct}%`, backgroundColor: getTierColor(tier), opacity: 0.8 }}
                className="flex items-center justify-center text-xs font-bold font-mono text-black transition-all"
                title={`${tier}: ${count} (${pct.toFixed(0)}%)`}>
                {count > 0 && `${count}`}
              </div>
            );
          })}
        </div>
        <div className="flex justify-between mt-2 text-xs font-mono">
          {['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4'].map((tier) => (
            <span key={tier} style={{ color: getTierColor(tier) }}>
              {tier.replace('_', ' ')}: {catalysts.filter((c) => c.tier === tier).length}
            </span>
          ))}
        </div>
      </div>

      {/* 30-Day Pipeline — top 10 only */}
      {next30.length > 0 && (
        <div className="bg-gray-900 border border-gray-700 p-4">
          <div className="text-xs text-gray-400 mb-3 font-mono flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Flame size={12} className="text-orange-400" />
              NEXT 30 DAYS — {next30.length} EVENTS
            </div>
            {next30.length > 10 && (
              <button onClick={() => onNavigate('screener')} className="text-blue-400 hover:text-blue-300 transition flex items-center gap-1">
                View all <ChevronRight size={12} />
              </button>
            )}
          </div>
          <div className="space-y-1">
            {next30.slice(0, 10).map((cat, i) => (
              <div key={cat.id} onClick={() => onExpandCatalyst(cat)}
                className="flex items-center gap-2 sm:gap-4 p-2 hover:bg-gray-800 cursor-pointer transition border-l-2"
                style={{ borderLeftColor: getTierColor(cat.tier) }}>
                <span className="text-xs text-gray-600 font-mono w-4 hidden sm:block">{i + 1}</span>
                <span className="text-xs text-gray-500 font-mono w-20 flex-shrink-0">{formatDate(cat.date)}</span>
                <span className="font-bold text-white text-sm w-14 flex-shrink-0">{cat.ticker}</span>
                <span className="text-sm text-gray-400 flex-1 truncate hidden sm:block">{cat.drug}</span>
                <span className="font-bold font-mono tabular-nums text-sm flex-shrink-0" style={{ color: getTierColor(cat.tier) }}>
                  {fmtProb(cat.prob)}%
                </span>
                <span className={`px-2 py-0.5 text-xs font-mono font-bold ${getTierBgClass(cat.tier)} hidden sm:block`}>
                  {cat.tier.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
          {next30.length > 10 && (
            <div className="mt-3 pt-3 border-t border-gray-800 text-center">
              <button onClick={() => onNavigate('screener')} className="text-sm text-blue-400 hover:text-blue-300 font-mono transition">
                + {next30.length - 10} more events — Open Screener
              </button>
            </div>
          )}
        </div>
      )}

      {/* CTA Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <button onClick={() => onNavigate('screener')}
          className="bg-gray-900 border border-gray-700 hover:border-blue-500 p-4 text-left transition group">
          <div className="flex items-center justify-between mb-2">
            <BarChart3 size={16} className="text-blue-400" />
            <ChevronRight size={14} className="text-gray-600 group-hover:text-blue-400 transition" />
          </div>
          <div className="text-sm font-bold text-white font-mono">Full Screener</div>
          <div className="text-xs text-gray-500 mt-1">Sort, filter, and compare all {catalysts.length} catalysts</div>
        </button>
        <button onClick={() => onNavigate('calendar')}
          className="bg-gray-900 border border-gray-700 hover:border-blue-500 p-4 text-left transition group">
          <div className="flex items-center justify-between mb-2">
            <Calendar size={16} className="text-purple-400" />
            <ChevronRight size={14} className="text-gray-600 group-hover:text-blue-400 transition" />
          </div>
          <div className="text-sm font-bold text-white font-mono">PDUFA Calendar</div>
          <div className="text-xs text-gray-500 mt-1">Month-by-month view of all decision dates</div>
        </button>
        <button onClick={() => onNavigate('intel')}
          className="bg-gray-900 border border-gray-700 hover:border-blue-500 p-4 text-left transition group">
          <div className="flex items-center justify-between mb-2">
            <Brain size={16} className="text-yellow-400" />
            <ChevronRight size={14} className="text-gray-600 group-hover:text-blue-400 transition" />
          </div>
          <div className="text-sm font-bold text-white font-mono">ODIN Intel</div>
          <div className="text-xs text-gray-500 mt-1">Historical approval rates, engine stats, TA risk</div>
        </button>
      </div>
    </div>
  );
};

// ── Calendar View ──────────────────────────────────
const CalendarView = ({ catalysts, onExpandCatalyst }) => {
  const months = useMemo(() => {
    const monthMap = {};
    catalysts.forEach((c) => {
      const date = new Date(c.date);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      if (!monthMap[key]) monthMap[key] = [];
      monthMap[key].push(c);
    });
    return monthMap;
  }, [catalysts]);

  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  return (
    <div className="space-y-6">
      {Object.entries(months).map(([monthKey, monthCatalysts]) => {
        const [year, month] = monthKey.split('-');
        const monthName = monthNames[parseInt(month) - 1];
        const tier1 = monthCatalysts.filter(c => c.tier === 'TIER_1').length;

        return (
          <div key={monthKey} className="border border-gray-700 p-4 bg-gray-900">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-mono text-gray-400 uppercase">
                {monthName} {year} <span className="text-gray-600">— {monthCatalysts.length} events</span>
              </h3>
              {tier1 > 0 && <span className="text-xs text-green-400 font-mono">{tier1} TIER 1</span>}
            </div>
            <div className="space-y-2">
              {monthCatalysts.map((catalyst) => (
                <div key={catalyst.id} onClick={() => onExpandCatalyst(catalyst)}
                  className="flex items-center gap-2 sm:gap-4 p-3 hover:bg-gray-800 cursor-pointer transition border-l-2"
                  style={{ borderLeftColor: getTierColor(catalyst.tier) }}>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{catalyst.ticker}</span>
                        <span className="text-xs text-gray-500">{catalyst.type}</span>
                        {catalyst.designations.length > 0 && (
                          <span className="text-xs text-blue-400 bg-blue-950 px-1 border border-blue-800 font-mono hidden sm:inline">
                            {catalyst.designations[0].replace('Breakthrough Therapy', 'BTD').replace('Priority Review', 'PR').replace('Orphan Drug', 'OD')}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-gray-400 ml-2 font-mono">{formatDate(catalyst.date)}</span>
                    </div>
                    <div className="flex justify-between items-center mt-1">
                      <div className="text-sm text-gray-400 truncate">{catalyst.drug}</div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {catalyst.weekend && <AlertTriangle size={12} className="text-red-400" />}
                        <span className="text-sm font-bold font-mono tabular-nums" style={{ color: getTierColor(catalyst.tier) }}>
                          {fmtProb(catalyst.prob)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ── Screener View ──────────────────────────────────
const ScreenerView = ({ catalysts, onExpandCatalyst }) => {
  const [filterTier, setFilterTier] = useState(null);
  const [filterTA, setFilterTA] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortCol, setSortCol] = useState('date');
  const [sortDir, setSortDir] = useState('asc');

  const tas = useMemo(() => [...new Set(catalysts.map((c) => c.ta))].sort(), [catalysts]);

  const filtered = useMemo(() => {
    return catalysts.filter((c) => {
      if (filterTier && c.tier !== filterTier) return false;
      if (filterTA && c.ta !== filterTA) return false;
      if (searchTerm && !c.drug.toLowerCase().includes(searchTerm.toLowerCase()) &&
          !c.ticker.toLowerCase().includes(searchTerm.toLowerCase()) &&
          !c.company.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      return true;
    });
  }, [catalysts, filterTier, filterTA, searchTerm]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) => {
      let aVal = a[sortCol];
      let bVal = b[sortCol];
      if (typeof aVal === 'string') { aVal = aVal.toLowerCase(); bVal = bVal.toLowerCase(); }
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return copy;
  }, [filtered, sortCol, sortDir]);

  const handleSort = (col) => {
    if (sortCol === col) { setSortDir(sortDir === 'asc' ? 'desc' : 'asc'); }
    else { setSortCol(col); setSortDir('asc'); }
  };

  return (
    <div className="space-y-4">
      <div className="bg-gray-900 border border-gray-700 p-4 space-y-3">
        <div className="flex gap-2 items-center">
          <Search size={16} className="text-gray-400" />
          <input type="text" placeholder="Search drug, ticker, company..."
            value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500" />
        </div>
        <div className="flex flex-wrap gap-2">
          <div>
            <label className="text-xs text-gray-400 block mb-2">Tier</label>
            <div className="flex gap-1 flex-wrap">
              {[null, 'TIER_1', 'TIER_2', 'TIER_3', 'TIER_4'].map((tier) => (
                <button key={tier || 'all'} onClick={() => setFilterTier(tier)}
                  className={`px-3 py-1 text-xs font-mono border transition ${
                    filterTier === tier ? 'bg-blue-900 border-blue-500 text-blue-300' : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
                  }`}>
                  {tier ? tier.replace('_', ' ') : 'All'}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1 min-w-32">
            <label className="text-xs text-gray-400 block mb-2">TA</label>
            <select value={filterTA || ''} onChange={(e) => setFilterTA(e.target.value || null)}
              className="w-full bg-gray-800 border border-gray-700 px-3 py-1 text-xs text-white focus:outline-none focus:border-blue-500">
              <option value="">All Therapeutic Areas</option>
              {tas.map((ta) => <option key={ta} value={ta}>{ta}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm font-mono">
            <thead>
              <tr className="border-b border-gray-700 bg-gray-800">
                {[
                  { col: 'date', label: 'Date' },
                  { col: 'ticker', label: 'Ticker' },
                  { col: 'drug', label: 'Drug' },
                  { col: 'indication', label: 'Indication' },
                  { col: 'ta', label: 'TA' },
                  { col: 'prob', label: 'Prob %' },
                  { col: 'tier', label: 'Tier' },
                ].map((col) => (
                  <th key={col.col} onClick={() => handleSort(col.col)}
                    className="px-2 sm:px-4 py-3 text-left text-gray-400 cursor-pointer hover:text-white transition uppercase text-xs font-bold whitespace-nowrap">
                    {col.label} {sortCol === col.col && (sortDir === 'asc' ? '\u25B2' : '\u25BC')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((cat) => (
                <tr key={cat.id} onClick={() => onExpandCatalyst(cat)}
                  className="border-b border-gray-800 hover:bg-gray-800 cursor-pointer transition">
                  <td className="px-2 sm:px-4 py-3 text-gray-300 text-xs whitespace-nowrap">{formatDate(cat.date)}</td>
                  <td className="px-2 sm:px-4 py-3 font-bold text-white">{cat.ticker}</td>
                  <td className="px-2 sm:px-4 py-3 text-gray-300 max-w-32 truncate">{cat.drug}</td>
                  <td className="px-2 sm:px-4 py-3 text-gray-400 text-xs max-w-32 truncate hidden sm:table-cell">{cat.indication}</td>
                  <td className="px-2 sm:px-4 py-3 text-gray-400 text-xs hidden sm:table-cell">{cat.ta}</td>
                  <td className="px-2 sm:px-4 py-3 font-bold font-mono tabular-nums" style={{ color: getTierColor(cat.tier) }}>
                    {fmtProb(cat.prob)}%
                  </td>
                  <td className="px-2 sm:px-4 py-3">
                    <span className={`px-2 py-1 text-xs font-bold inline-block ${getTierBgClass(cat.tier)}`}>
                      {cat.tier}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="text-xs text-gray-500 font-mono">Showing {sorted.length} of {catalysts.length} catalysts</div>
    </div>
  );
};

// ── Intel View (NEW) — Historical rates, TA heatmap ──
const IntelView = ({ catalysts }) => {
  const taGroups = useMemo(() => {
    const groups = {};
    catalysts.forEach((c) => {
      if (!groups[c.ta]) groups[c.ta] = [];
      groups[c.ta].push(c);
    });
    return groups;
  }, [catalysts]);

  const sortedRates = Object.entries(HIST_APPROVAL_RATES)
    .sort((a, b) => b[1].rate - a[1].rate);

  return (
    <div className="space-y-6">
      {/* Historical Approval Rates */}
      <div className="bg-gray-900 border border-gray-700 p-4">
        <div className="flex items-center gap-2 mb-4">
          <PieChart size={14} className="text-blue-400" />
          <div className="text-xs text-gray-400 font-mono uppercase">HISTORICAL FDA APPROVAL RATES BY THERAPEUTIC AREA</div>
        </div>
        <div className="text-xs text-gray-500 mb-4">Based on 486-event backtest (2018-2025 PDUFA decisions)</div>
        <div className="space-y-2">
          {sortedRates.map(([ta, data]) => {
            const activeCatalysts = taGroups[ta] || [];
            return (
              <div key={ta} className="flex items-center gap-3 text-sm">
                <span className="text-gray-300 w-36 sm:w-44 truncate text-xs font-mono">{ta}</span>
                <div className="flex-1 bg-gray-800 h-5 overflow-hidden relative">
                  <div className="h-full transition-all duration-500"
                    style={{ width: `${data.rate}%`, backgroundColor: data.rate >= 85 ? '#22c55e' : data.rate >= 75 ? '#eab308' : data.rate >= 65 ? '#f97316' : '#ef4444', opacity: 0.7 }} />
                  <span className="absolute inset-0 flex items-center px-2 text-xs font-mono text-gray-200">
                    {data.rate.toFixed(1)}% ({data.approved}/{data.total})
                  </span>
                </div>
                {activeCatalysts.length > 0 && (
                  <span className="text-xs text-blue-400 font-mono w-16 text-right">{activeCatalysts.length} active</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* TA Risk Classification */}
      <div className="bg-gray-900 border border-gray-700 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={14} className="text-blue-400" />
          <div className="text-xs text-gray-400 font-mono uppercase">ODIN TA RISK CLASSIFICATION</div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: 'LOW RISK', color: 'green', areas: ['Oncology', 'Immunology', 'Dermatology', 'Vaccines', 'Infectious Disease'], desc: 'Historically high approval rates, well-established regulatory pathways' },
            { label: 'MODERATE RISK', color: 'yellow', areas: ['CNS', 'Cardiovascular', 'Metabolic', 'Rare Disease', 'Respiratory'], desc: 'Mixed track record, often complex endpoints or safety profiles' },
            { label: 'HIGH RISK', color: 'red', areas: ['Ophthalmology', 'GI/Hepatology', 'Nephrology', 'Hematology', 'Musculoskeletal'], desc: 'Below-average approval rates, challenging regulatory landscape' },
          ].map((risk) => (
            <div key={risk.label} className={`bg-gray-800 border border-${risk.color}-800 p-4`}>
              <div className={`text-xs font-mono font-bold text-${risk.color}-400 mb-2`}>{risk.label}</div>
              <div className="space-y-1 mb-3">
                {risk.areas.map((a) => (
                  <div key={a} className="text-xs text-gray-300 flex justify-between">
                    <span>{a}</span>
                    {HIST_APPROVAL_RATES[a] && (
                      <span className="text-gray-500 font-mono">{HIST_APPROVAL_RATES[a].rate.toFixed(0)}%</span>
                    )}
                  </div>
                ))}
              </div>
              <div className="text-xs text-gray-500">{risk.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ODIN Model Stats */}
      <div className="bg-gray-900 border border-gray-700 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Brain size={14} className="text-blue-400" />
          <div className="text-xs text-gray-400 font-mono uppercase">ODIN v10.66 ENGINE STATS</div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          {[
            { label: 'Parameters', value: '33' },
            { label: 'Base Probability', value: '83.4%' },
            { label: 'Backtest Events', value: '486' },
            { label: 'Architecture', value: 'GPU Logistic' },
          ].map((stat) => (
            <div key={stat.label} className="bg-gray-800 p-3 border border-gray-700">
              <div className="text-xs text-gray-500 mb-1">{stat.label}</div>
              <div className="text-lg font-bold text-blue-400 font-mono">{stat.value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════
// ── FDA Disclaimer Modal ──────────────────────────
// ── Password Gate (dev mode) ──────────────────────
const PasswordGate = ({ onUnlock }) => {
  const [pw, setPw] = useState('');
  const [error, setError] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (pw === '1U670NnGEhN6!Hv4Z7tJOd5Z%I9h') {
      try { sessionStorage.setItem('pdufa_unlocked', 'true'); } catch (e) {}
      onUnlock();
    } else {
      setError(true);
      setPw('');
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-950 z-[99999] flex items-center justify-center p-4">
      <div className="text-center max-w-sm w-full">
        <h1 className="text-3xl font-bold font-mono mb-1">
          PDUFA<span className="text-blue-400">.BIO</span>
        </h1>
        <div className="text-xs text-yellow-500 font-mono mb-6 bg-yellow-500/10 border border-yellow-800 px-3 py-1.5 inline-block">
          UNDER CONSTRUCTION
        </div>
        <p className="text-sm text-gray-400 mb-6">
          This site is currently being rebuilt. Enter the access code to continue.
        </p>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="password"
            value={pw}
            onChange={(e) => { setPw(e.target.value); setError(false); }}
            placeholder="Access code"
            className={`w-full bg-gray-900 border ${error ? 'border-red-500' : 'border-gray-700'} text-white px-4 py-3 font-mono text-sm text-center focus:outline-none focus:border-blue-500 transition`}
            autoFocus
          />
          {error && <div className="text-xs text-red-400 font-mono">Incorrect access code</div>}
          <button type="submit"
            className="w-full bg-blue-600 hover:bg-blue-500 text-white py-3 font-mono text-sm font-bold transition">
            ENTER
          </button>
        </form>
        <p className="text-[10px] text-gray-600 mt-6 font-mono">Powered by ODIN v10.66</p>
      </div>
    </div>
  );
};

const DisclaimerModal = ({ onAccept }) => {
  const [checked, setChecked] = useState(false);

  return (
    <div className="fixed inset-0 bg-black/90 z-[9999] flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 max-w-lg w-full">
        {/* Header */}
        <div className="bg-red-950 border-b border-red-800 p-4 sm:p-6">
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle size={24} className="text-red-400 flex-shrink-0" />
            <h2 className="text-lg sm:text-xl font-bold text-white font-mono">IMPORTANT DISCLAIMER</h2>
          </div>
          <p className="text-red-300 text-sm font-mono">Please read and acknowledge before continuing</p>
        </div>

        {/* Body */}
        <div className="p-4 sm:p-6 space-y-4 text-sm text-gray-300 leading-relaxed max-h-[50vh] overflow-y-auto">
          <p>
            <strong className="text-white">PDUFA.BIO is not affiliated with, endorsed by, or connected to the U.S. Food & Drug Administration (FDA)</strong> or any government agency. The name "PDUFA" refers to the Prescription Drug User Fee Act and is used here solely to describe the subject matter of this site.
          </p>
          <p>
            <strong className="text-white">This is not financial advice.</strong> PDUFA.BIO is not a registered investment advisor, broker-dealer, or financial planner. Nothing on this site constitutes a recommendation to buy, sell, or hold any security.
          </p>
          <p>
            <strong className="text-white">Probability scores are machine-learning model outputs, not guarantees.</strong> The ODIN scoring engine produces statistical estimates based on historical data and publicly available information. These scores reflect mathematical probabilities derived from pattern recognition — they do not predict the future and should not be the sole basis for any investment decision.
          </p>
          <p>
            <strong className="text-white">No liability for losses.</strong> PDUFA.BIO, its operators, contributors, and affiliates accept no responsibility or liability for any financial losses, damages, or consequences arising from the use of information presented on this site. All investment decisions carry risk, including the risk of total loss.
          </p>
          <p className="text-gray-500 text-xs">
            By clicking below, you acknowledge that you have read, understood, and agree to these terms. You accept full responsibility for your own investment decisions.
          </p>
        </div>

        {/* Checkbox + Button */}
        <div className="border-t border-gray-700 p-4 sm:p-6 space-y-4">
          <button
            onClick={() => setChecked(!checked)}
            className="flex items-start gap-3 w-full text-left group"
          >
            {checked
              ? <CheckSquare size={20} className="text-blue-400 flex-shrink-0 mt-0.5" />
              : <Square size={20} className="text-gray-600 group-hover:text-gray-400 flex-shrink-0 mt-0.5 transition" />
            }
            <span className={`text-sm ${checked ? 'text-white' : 'text-gray-400'} transition`}>
              I understand that PDUFA.BIO is not affiliated with the FDA, this is not financial advice, and probability scores are model outputs — not guarantees of FDA approval or stock performance.
            </span>
          </button>
          <button
            onClick={() => {
              if (checked) {
                try { localStorage.setItem('pdufa_disclaimer_accepted', 'true'); } catch (e) {}
                onAccept();
              }
            }}
            disabled={!checked}
            className={`w-full py-3 font-mono text-sm font-bold transition ${
              checked
                ? 'bg-blue-600 hover:bg-blue-500 text-white cursor-pointer'
                : 'bg-gray-800 text-gray-600 cursor-not-allowed'
            }`}
          >
            {checked ? 'I UNDERSTAND — ENTER PDUFA.BIO' : 'CHECK THE BOX ABOVE TO CONTINUE'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Main App ──────────────────────────────────────
export default function PdufaBio() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCatalyst, setSelectedCatalyst] = useState(null);
  const [siteUnlocked, setSiteUnlocked] = useState(() => {
    try { return sessionStorage.getItem('pdufa_unlocked') === 'true'; } catch (e) { return false; }
  });
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(() => {
    try { return localStorage.getItem('pdufa_disclaimer_accepted') === 'true'; } catch (e) { return false; }
  });
  const today = new Date();
  const dateStr = `${today.toLocaleString('en-US', { weekday: 'short' })} ${today.toLocaleString('en-US', { month: 'short' })} ${today.getDate()}, ${today.getFullYear()}`;

  const sortedCatalysts = useMemo(
    () => [...CATALYSTS_DATA].sort((a, b) => new Date(a.date) - new Date(b.date)),
    []
  );

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'calendar', label: 'Calendar', icon: Calendar },
    { id: 'screener', label: 'Screener', icon: BarChart3 },
    { id: 'intel', label: 'Intel', icon: Brain },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white font-sans">
      {/* Password Gate */}
      {!siteUnlocked && (
        <PasswordGate onUnlock={() => setSiteUnlocked(true)} />
      )}

      {/* Disclaimer Modal (only after password gate) */}
      {siteUnlocked && !disclaimerAccepted && (
        <DisclaimerModal onAccept={() => setDisclaimerAccepted(true)} />
      )}

      {/* Top Bar */}
      <div className="border-b border-gray-700 bg-gray-900 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-3 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight cursor-pointer" onClick={() => setActiveTab('dashboard')}>
              PDUFA<span className="text-blue-400">.BIO</span>
            </h1>
            <div className="bg-gray-800 border border-gray-700 px-2 py-0.5 text-xs font-mono text-blue-400 hidden sm:block">
              ODIN v10.66
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden lg:flex items-center gap-4 text-xs font-mono text-gray-500">
              <span>Engine: <span className="text-green-400">v10.66</span></span>
              <span>Params: <span className="text-green-400">33</span></span>
              <span>Events: <span className="text-green-400">{CATALYSTS_DATA.length}</span></span>
            </div>
            <div className="text-xs sm:text-sm text-gray-400 font-mono">{dateStr}</div>
          </div>
        </div>
      </div>

      {/* Nav Tabs */}
      <div className="border-b border-gray-700 bg-gray-900 sticky top-[53px] z-30">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 flex gap-0 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`px-3 sm:px-6 py-3 sm:py-4 font-mono text-xs sm:text-sm uppercase border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === tab.id ? 'border-blue-400 text-blue-400' : 'border-transparent text-gray-400 hover:text-gray-300'
                }`}>
                <Icon size={14} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-3 sm:px-6 py-4 sm:py-8">
        {activeTab === 'dashboard' && <DashboardView catalysts={sortedCatalysts} onExpandCatalyst={setSelectedCatalyst} onNavigate={setActiveTab} />}
        {activeTab === 'calendar' && <CalendarView catalysts={sortedCatalysts} onExpandCatalyst={setSelectedCatalyst} />}
        {activeTab === 'screener' && <ScreenerView catalysts={sortedCatalysts} onExpandCatalyst={setSelectedCatalyst} />}
        {activeTab === 'intel' && <IntelView catalysts={sortedCatalysts} />}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-800 bg-gray-900 mt-8">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-6 sm:py-8">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-6">
            <div>
              <h4 className="text-sm font-bold font-mono text-white mb-2">PDUFA<span className="text-blue-400">.BIO</span></h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                FDA catalyst intelligence powered by the ODIN v10.66 scoring engine.
                Trained on 486 historical PDUFA decisions (2018–2025).
              </p>
            </div>
            <div>
              <h4 className="text-xs font-bold font-mono text-gray-400 mb-2">NAVIGATE</h4>
              <div className="space-y-1">
                {tabs.map(t => (
                  <button key={t.id} onClick={() => setActiveTab(t.id)} className="block text-xs text-gray-500 hover:text-blue-400 font-mono transition">
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <h4 className="text-xs font-bold font-mono text-gray-400 mb-2">ENGINE</h4>
              <div className="text-xs text-gray-500 space-y-1 font-mono">
                <div>Version: <span className="text-green-400">v10.66 Dynamic Grandmaster</span></div>
                <div>Parameters: <span className="text-gray-300">33</span></div>
                <div>Training Set: <span className="text-gray-300">486 events</span></div>
                <div>Model: <span className="text-gray-300">GPU Logistic Regression</span></div>
              </div>
            </div>
          </div>

          {/* Legal */}
          <div className="border-t border-gray-800 pt-4 space-y-3">
            <p className="text-[10px] sm:text-xs text-gray-600 leading-relaxed">
              <strong className="text-gray-500">DISCLAIMER:</strong> PDUFA.BIO is not affiliated with, endorsed by, or connected to the U.S. Food & Drug Administration (FDA) or any government agency. The name "PDUFA" refers to the Prescription Drug User Fee Act and is used descriptively. This site does not provide financial, investment, legal, or medical advice. PDUFA.BIO is not a registered investment advisor, broker-dealer, or financial planner. Probability scores are generated by machine-learning models based on historical data and publicly available information. These scores are statistical estimates, not predictions or guarantees of FDA action or securities performance. Past approval rates do not guarantee future results.
            </p>
            <p className="text-[10px] sm:text-xs text-gray-600 leading-relaxed">
              <strong className="text-gray-500">RISK WARNING:</strong> Investing in biotechnology and pharmaceutical securities involves substantial risk, including the risk of total loss of capital. Binary catalyst events (such as PDUFA dates) can result in extreme price volatility. You should not invest money you cannot afford to lose. Always consult with a qualified financial advisor before making investment decisions. PDUFA.BIO, its operators, contributors, and affiliates accept no responsibility or liability for any losses arising from use of this site.
            </p>
            <div className="flex flex-col sm:flex-row justify-between items-center gap-2 pt-2">
              <span className="text-[10px] text-gray-600 font-mono">&copy; {new Date().getFullYear()} PDUFA.BIO — All rights reserved.</span>
              <span className="text-[10px] text-gray-700 font-mono">Market data via FMP &middot; Social data via LunarCrush</span>
            </div>
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedCatalyst && (
        <DetailModal catalyst={selectedCatalyst} onClose={() => setSelectedCatalyst(null)} />
      )}
    </div>
  );
}
