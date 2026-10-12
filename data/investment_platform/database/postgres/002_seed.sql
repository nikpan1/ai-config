insert into investor values ('INV-100','ACTIVE'),('INV-200','PENDING'),('INV-300','SUSPENDED');
insert into questionnaire_version values ('Q1','2025-01-01T00:00:00Z',true),('Q2','2026-01-01T00:00:00Z',true),('Q3','2026-09-01T00:00:00Z',false);
insert into dictionary_code(dictionary_name,code,revision,label,retired) values
('experience-level','NONE','D-2026-09','No experience',false),
('experience-level','BEGINNER','D-2026-09','Beginner',false),
('experience-level','INTERMEDIATE','D-2026-09','Intermediate',false),
('experience-level','ADVANCED','D-2026-09','Advanced',false),
('investment-horizon','H0','D-2026-09','Under one year',false),
('investment-horizon','H1','D-2026-09','One to three years',false),
('investment-horizon','H3','D-2026-09','Three to seven years',false),
('investment-horizon','H7','D-2026-09','Seven years or more',false),
('loss-tolerance','L0','D-2026-09','No loss accepted',false),
('loss-tolerance','L5','D-2026-09','Up to five percent',false),
('loss-tolerance','L10','D-2026-09','Up to ten percent',false),
('loss-tolerance','L20','D-2026-09','Above ten percent',false),
('liquidity-need','IMMEDIATE','D-2026-09','Immediate',false),
('liquidity-need','SOON','D-2026-09','Soon',false),
('liquidity-need','FLEXIBLE','D-2026-09','Flexible',false),
('liquidity-need','LONG_TERM','D-2026-09','Long term',false),
('experience-level','EXPERT','D-2026-09','Expert',true);
