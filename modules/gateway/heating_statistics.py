"""Counter deltas and sampled relay time; never a flame or energy measurement."""


def summarize(samples, hours, now, max_gap=120):
    start=now-hours*3600
    count={1:6,6:12,24:24}[hours]
    width=hours*3600/count
    bins=[{'ts':start+i*width,'starts':None,'relay_minutes':None,'coverage_seconds':0} for i in range(count)]
    coverage=runtime=starts=0
    resets=gaps=0
    first=last=None

    def counter(row):
        value=row.get('anlage.starts')
        return value if type(value) is int and 0<=value<=65535 else None

    def relay(row):
        stage1,stage2=row.get('anlage.burner'),row.get('anlage.burner_stage2')
        if stage1 is True or stage2 is True:
            return True
        return False if stage1 is False and stage2 is False else None

    for a,b in zip(samples,samples[1:]):
        dt=b['ts']-a['ts']
        if a['ts']<start or b['ts']>now or dt<=0:
            continue
        ca,cb=counter(a),counter(b)
        ra,rb=relay(a),relay(b)
        if dt>max_gap or ca is None or cb is None or ra is None or rb is None:
            gaps+=1
            continue
        delta=cb-ca
        if delta<0:
            if ca>=65000 and cb<=1000:
                delta+=65536
            else:
                resets+=1
                continue
        coverage+=dt
        runtime+=dt if ra else 0
        starts+=delta
        first=a['ts'] if first is None else first
        last=b['ts']
        # Counter increments belong to the observation at b; relay time is
        # piecewise constant from a until the next sampled state.
        for i,item in enumerate(bins):
            overlap=max(0,min(b['ts'],start+(i+1)*width)-max(a['ts'],start+i*width))
            if overlap:
                item['coverage_seconds']+=overlap
                item['starts']=item['starts'] or 0
                item['relay_minutes']=(item['relay_minutes'] or 0)+(overlap/60 if ra else 0)
        index=min(count-1,int((b['ts']-start)/width))
        if bins[index]['starts'] is None:
            # An exact bucket boundary is assigned to the preceding observed bin.
            index=max(0,index-1)
        bins[index]['starts']=(bins[index]['starts'] or 0)+delta
    for item in bins:
        if item['relay_minutes'] is not None:
            item['relay_minutes']=round(item['relay_minutes'],2)
    return {'hours':hours,'coverage_seconds':coverage,'coverage_percent':round(coverage/(hours*36),1),
            'observed_from':first,'observed_to':last,'starts':starts if coverage else None,
            'relay_runtime_minutes':round(runtime/60,2) if coverage else None,
            'starts_per_hour':round(starts/(coverage/3600),2) if coverage else None,
            'relay_minutes_per_start':round(runtime/60/starts,2) if starts else None,
            'counter_resets':resets,'excluded_intervals':gaps,'bins':bins,
            'measurement':'Regler-Startzähler und abgetastete Relaiskontakte K4/K5; keine Flammenmessung.'}
