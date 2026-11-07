#!/usr/bin/env python3
"""Generate the publication Figure 2 panels and composite for SNP2Cluster-Py.

Example:
  python generate_figure2_context_comparison.py \
    --st-only-core ST_only/core_snp_clusters.csv \
    --facility-st-core Facility_ST/core_snp_clusters.csv \
    --metadata bgerms_study_metadata_klepp.csv \
    --facility-order "Hospital A,Hospital B,Hospital C,Hospital D,Hospital E,Hospital F" \
    --outdir figure2_outputs

Dependencies: pandas, numpy, matplotlib.
The script reads clustered status directly from non-missing core_snp_cluster values.
"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

import argparse, os
parser=argparse.ArgumentParser(description='Generate Figure 2 panels comparing ST-only and Facility+ST Core clustering.')
parser.add_argument('--st-only-core', required=True, help='Complete ST-only core_snp_clusters.csv')
parser.add_argument('--facility-st-core', required=True, help='Complete Facility+ST core_snp_clusters.csv')
parser.add_argument('--metadata', required=True, help='Metadata CSV containing sampleid, st_type, and hospital')
parser.add_argument('--outdir', default='figure2_outputs')
parser.add_argument('--sample-id-column', default='sampleid')
parser.add_argument('--st-column', default='st_type')
parser.add_argument('--facility-column', default='hospital')
parser.add_argument('--cluster-column', default='core_snp_cluster')
parser.add_argument('--facility-order', default=None, help='Comma-separated facility order; default is sorted observed values')
args=parser.parse_args()
os.makedirs(args.outdir, exist_ok=True)
meta=pd.read_csv(args.metadata)
fac=pd.read_csv(args.facility_st_core)
st_core=pd.read_csv(args.st_only_core)
sid, stcol, faccol, clcol = args.sample_id_column, args.st_column, args.facility_column, args.cluster_column
for name,df,required in [('metadata',meta,[sid,stcol,faccol]),('ST-only Core table',st_core,[sid,clcol]),('Facility+ST Core table',fac,[sid,clcol])]:
    missing=[c for c in required if c not in df.columns]
    if missing: raise ValueError(f'{name} is missing required columns: {missing}')
for name,df in [('metadata',meta),('ST-only Core table',st_core),('Facility+ST Core table',fac)]:
    if df[sid].duplicated().any(): raise ValueError(f'{name} contains duplicate sample IDs')
# Clustered status is read directly from the authoritative complete Core tables.
base=meta[[sid,stcol,faccol]].copy().rename(columns={sid:'sampleid',stcol:'st_type',faccol:'hospital'})
base=base.merge(st_core[[sid,clcol]].rename(columns={'core_snp_cluster':'st_core_cluster'}),on='sampleid',how='left',validate='one_to_one')
base=base.merge(fac[[sid,clcol]].rename(columns={'core_snp_cluster':'facility_st_core_cluster'}),on='sampleid',how='left',validate='one_to_one')
base['st_clustered']=base.st_core_cluster.notna()
base['facility_st_clustered']=base.facility_st_core_cluster.notna()
assert len(base)==len(meta), 'Metadata and Core tables do not contain the same unique sample population.'

# No isolate identifiers are embedded; all assignments are read from the two Core tables.

# Panel A
A=base.groupby('st_type').agg(total=('sampleid','size'),clustered=('st_clustered','sum')).reset_index(); A['unclustered']=A.total-A.clustered
single=A[A.total==1]; A=A[A.total>=2].copy()
if len(single): A=pd.concat([A,pd.DataFrame([{'st_type':f'Singleton STs ({len(single)})','total':int(single.total.sum()),'clustered':int(single.clustered.sum()),'unclustered':int(single.unclustered.sum())}])],ignore_index=True)
A=A.sort_values(['total','clustered'],ascending=False)
# Panel B
T=base.pivot_table(index='st_type',columns='hospital',values='sampleid',aggfunc='count',fill_value=0)
C=base.pivot_table(index='st_type',columns='hospital',values='facility_st_clustered',aggfunc='sum',fill_value=0)
keep=T.index[(T.sum(axis=1)>=2)&(T.max(axis=1)>=2)]
keep=T.loc[keep].sum(axis=1).sort_values(ascending=False).index
cols=[x.strip() for x in args.facility_order.split(',')] if args.facility_order else sorted(base['hospital'].dropna().astype(str).unique())
T=T.loc[keep].reindex(columns=cols,fill_value=0); C=C.loc[keep].reindex(columns=cols,fill_value=0); P=(C/T.replace(0,np.nan)).fillna(0)
# Panel C
ct=np.array([[int((base.st_clustered & base.facility_st_clustered).sum()),int((base.st_clustered & ~base.facility_st_clustered).sum())],[int((~base.st_clustered & base.facility_st_clustered).sum()),int((~base.st_clustered & ~base.facility_st_clustered).sum())]])
print('transition',ct,'fac by hospital',base.groupby('hospital').facility_st_clustered.sum().to_dict())

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})

def save(fig,stem):
 for ext in ['png','pdf','svg']:
  fig.savefig(os.path.join(args.outdir, f'{stem}.{ext}'),dpi=300 if ext=='png' else None,bbox_inches='tight',facecolor='white')

# A 1800x1800
fig,ax=plt.subplots(figsize=(6,6)); y=np.arange(len(A)); ax.barh(y,A.clustered,color='#0072B2',edgecolor='black',lw=.4,label='Clustered'); ax.barh(y,A.unclustered,left=A.clustered,color='#D0D0D0',edgecolor='black',lw=.4,label='Unclustered'); labels=[x if str(x).startswith('Singleton') else f'ST{x}' for x in A.st_type]; ax.set_yticks(y,labels,fontsize=8); ax.invert_yaxis(); ax.set_xlabel('Eligible isolates'); ax.set_title('A  ST-only Core clustering',loc='left',fontweight='bold'); ax.legend(frameon=False,ncol=2,loc='lower right',fontsize=8); ax.grid(axis='x',alpha=.18); ax.spines[['top','right']].set_visible(False)
for yi,total in enumerate(A.total): ax.text(total+.15,yi,str(int(total)),va='center',fontsize=7)
fig.tight_layout(); save(fig,'Figure2A_ST_only_Core_clustering_corrected'); plt.close(fig)

# B 2100x2100
fig,ax=plt.subplots(figsize=(7,7)); cmap=LinearSegmentedColormap.from_list('p',['#f2f2f2','#b8e0d2','#009E73']); im=ax.imshow(P.values,aspect='auto',vmin=0,vmax=1,cmap=cmap); ax.set_xticks(range(len(cols)),[c.replace('Hospital ','Hospital\n') for c in cols],fontsize=9); ax.set_yticks(range(len(keep)),[f'ST{x}' for x in keep],fontsize=8); ax.set_title('B  Facility + ST Core clustering',loc='left',fontweight='bold'); ax.set_xlabel('Facility'); ax.set_ylabel('Sequence type')
for i in range(len(keep)):
 for j in range(len(cols)):
  n=int(T.iloc[i,j]); c=int(C.iloc[i,j]); ax.text(j,i,f'{c}/{n}' if n else '–',ha='center',va='center',fontsize=7,color='white' if n and P.iloc[i,j]>.62 else ('#999' if not n else 'black'),fontweight='bold' if n else 'normal')
cb=fig.colorbar(im,ax=ax,fraction=.035,pad=.02); cb.set_label('Proportion clustered'); ax.text(1,-.1,'Cell labels: clustered / eligible isolates',transform=ax.transAxes,ha='right',fontsize=8); [sp.set_visible(False) for sp in ax.spines.values()]; fig.tight_layout(); save(fig,'Figure2B_Facility_ST_Core_clustering_corrected'); plt.close(fig)

# C 2400x1200
fig,ax=plt.subplots(figsize=(8,4)); ax.axis('off'); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.set_title('C  Isolate-level transitions between Core contexts',loc='left',fontweight='bold',pad=8); x0,y0,w,h=.12,.18,.76,.62; rh=h/3; cw=w/3
for j,head in enumerate(['Facility + ST\nclustered','Facility + ST\nunclustered']): ax.add_patch(Rectangle((x0+(j+1)*cw,y0+2*rh),cw,rh,fc='#EAF2F8',ec='white')); ax.text(x0+(j+1.5)*cw,y0+2.5*rh,head,ha='center',va='center',fontweight='bold')
for i,lab in enumerate(['ST-only\nclustered','ST-only\nunclustered']): yy=y0+(1-i)*rh; ax.add_patch(Rectangle((x0,yy),cw,rh,fc='#EAF2F8',ec='white')); ax.text(x0+.5*cw,yy+.5*rh,lab,ha='center',va='center',fontweight='bold')
cols2=[['#009E73','#D55E00'],['#CC79A7','#7F7F7F']]; labs=[['Clustered in both','Became unclustered'],['Newly clustered','Unclustered in both']]
for i in range(2):
 yy=y0+(1-i)*rh
 for j in range(2):
  xx=x0+(j+1)*cw; n=int(ct[i,j]); ax.add_patch(Rectangle((xx,yy),cw,rh,fc=cols2[i][j],ec='white')); ax.text(xx+.5*cw,yy+.57*rh,f'{n} isolates\n({100*n/len(base):.1f}%)',ha='center',va='center',color='white',fontweight='bold',fontsize=12); ax.text(xx+.5*cw,yy+.18*rh,labs[i][j],ha='center',va='center',color='white',fontsize=8)
ax.text(.5,.06,f'All {len(base)} isolates evaluated in both contexts; clustered isolates: {int(base.st_clustered.sum())} → {int(base.facility_st_clustered.sum())}.',ha='center',fontsize=9); fig.tight_layout(); save(fig,'Figure2C_isolate_transitions_corrected'); plt.close(fig)

# composite 3600x4200 proportion
fig=plt.figure(figsize=(12,14)); gs=fig.add_gridspec(2,2,height_ratios=[1,0.65],hspace=.28,wspace=.28)
# recreate A
ax=fig.add_subplot(gs[0,0]); y=np.arange(len(A)); ax.barh(y,A.clustered,color='#0072B2',edgecolor='black',lw=.4,label='Clustered'); ax.barh(y,A.unclustered,left=A.clustered,color='#D0D0D0',edgecolor='black',lw=.4,label='Unclustered'); ax.set_yticks(y,labels,fontsize=8); ax.invert_yaxis(); ax.set_xlabel('Eligible isolates'); ax.set_title('A  ST-only Core clustering',loc='left',fontweight='bold'); ax.legend(frameon=False,ncol=2,loc='lower right',fontsize=8); ax.grid(axis='x',alpha=.18); ax.spines[['top','right']].set_visible(False)
for yi,total in enumerate(A.total): ax.text(total+.15,yi,str(int(total)),va='center',fontsize=7)
# recreate B
ax=fig.add_subplot(gs[0,1]); im=ax.imshow(P.values,aspect='auto',vmin=0,vmax=1,cmap=cmap); ax.set_xticks(range(len(cols)),[c.replace('Hospital ','Hospital\n') for c in cols],fontsize=8); ax.set_yticks(range(len(keep)),[f'ST{x}' for x in keep],fontsize=7); ax.set_title('B  Facility + ST Core clustering',loc='left',fontweight='bold'); ax.set_xlabel('Facility'); ax.set_ylabel('Sequence type')
for i in range(len(keep)):
 for j in range(len(cols)):
  n=int(T.iloc[i,j]); c=int(C.iloc[i,j]); ax.text(j,i,f'{c}/{n}' if n else '–',ha='center',va='center',fontsize=6,color='white' if n and P.iloc[i,j]>.62 else ('#999' if not n else 'black'),fontweight='bold' if n else 'normal')
cb=fig.colorbar(im,ax=ax,fraction=.04,pad=.02); cb.set_label('Proportion clustered',fontsize=8); ax.text(1,-.08,'Cell labels: clustered / eligible isolates',transform=ax.transAxes,ha='right',fontsize=7); [sp.set_visible(False) for sp in ax.spines.values()]
# C spanning
ax=fig.add_subplot(gs[1,:]); ax.axis('off'); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.set_title('C  Isolate-level transitions between Core contexts',loc='left',fontweight='bold',pad=8); x0,y0,w,h=.18,.15,.64,.68; rh=h/3; cw=w/3
for j,head in enumerate(['Facility + ST\nclustered','Facility + ST\nunclustered']): ax.add_patch(Rectangle((x0+(j+1)*cw,y0+2*rh),cw,rh,fc='#EAF2F8',ec='white')); ax.text(x0+(j+1.5)*cw,y0+2.5*rh,head,ha='center',va='center',fontweight='bold')
for i,lab in enumerate(['ST-only\nclustered','ST-only\nunclustered']): yy=y0+(1-i)*rh; ax.add_patch(Rectangle((x0,yy),cw,rh,fc='#EAF2F8',ec='white')); ax.text(x0+.5*cw,yy+.5*rh,lab,ha='center',va='center',fontweight='bold')
for i in range(2):
 yy=y0+(1-i)*rh
 for j in range(2):
  xx=x0+(j+1)*cw; n=int(ct[i,j]); ax.add_patch(Rectangle((xx,yy),cw,rh,fc=cols2[i][j],ec='white')); ax.text(xx+.5*cw,yy+.57*rh,f'{n} isolates\n({100*n/len(base):.1f}%)',ha='center',va='center',color='white',fontweight='bold',fontsize=12); ax.text(xx+.5*cw,yy+.18*rh,labs[i][j],ha='center',va='center',color='white',fontsize=8)
ax.text(.5,.04,f'All {len(base)} isolates evaluated in both contexts; clustered isolates: {int(base.st_clustered.sum())} → {int(base.facility_st_clustered.sum())}.',ha='center',fontsize=9)
fig.suptitle('Effect of Core clustering context on K. pneumoniae clustering',fontsize=16,fontweight='bold',y=.995)
fig.tight_layout(rect=[0,0,1,.98]); save(fig,'Figure2_context_comparison_corrected_composite'); plt.close(fig)

# support tables
A.to_csv(os.path.join(args.outdir,'Figure2A_ST_only_summary_corrected.csv'),index=False)
rows=[]
for stv in keep:
 for hosp in cols:
  n=int(T.loc[stv,hosp]); c=int(C.loc[stv,hosp])
  if n: rows.append({'ST':stv,'hospital':hosp,'eligible':n,'clustered':c,'unclustered':n-c,'proportion_clustered':c/n})
pd.DataFrame(rows).to_csv(os.path.join(args.outdir,'Figure2B_Facility_ST_summary_corrected.csv'),index=False)
pd.DataFrame({'ST_only':['Clustered','Clustered','Unclustered','Unclustered'],'Facility_ST':['Clustered','Unclustered','Clustered','Unclustered'],'n':[ct[0,0],ct[0,1],ct[1,0],ct[1,1]],'percent':[100*x/len(base) for x in [ct[0,0],ct[0,1],ct[1,0],ct[1,1]]]}).to_csv(os.path.join(args.outdir,'Figure2C_transition_table_corrected.csv'),index=False)
