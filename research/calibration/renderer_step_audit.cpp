#include "/Users/hiimdrdey/code/daw/autotune/VibeAutotune/CausalTDPSOLARenderer.h"
#include <cmath>
#include <iostream>
#include <vector>

int main() {
    constexpr double sr=48000, f=233.0818808, ratio=0.9438743127;
    // Align both commands to every tested host block size so a 256-sample
    // callback does not receive the command later than a 32-sample callback.
    constexpr int start=49152, end=98304, total=147456;
    bool ok=true;
    for (int latency : {1152, 2048})
    for (int block : {32, 64, 128, 256})
    for (int mode=0; mode<2; ++mode) {
        CausalTDPSOLARenderer r; r.prepare(sr,block,latency);
        std::vector<float> in(block),out(block), all; all.reserve(total);
        for (int s=0;s<total;s+=block) {
            const double q=s>=start && s<end ? ratio : 1.;
            for(int i=0;i<block;++i) in[i]=0.3f*std::sin(2*3.141592653589793*f*(s+i)/sr);
            if(mode==0) r.process(in.data(),out.data(),block,f,q,true);
            else r.process(in.data(),out.data(),block,f,q,true,false,f*q);
            all.insert(all.end(),out.begin(),out.end());
        }
        std::cout << "requested_ratio=" << ratio << " expected_hz=" << f*ratio << '\n';
        for (int offset : {-12000, 4096, 12000, 24000, 36000, 52000}) {
            int a=start+offset, b=a+8192; double energy=0; std::vector<double> z;
            for(int i=a+1;i<b;++i) { double x=all[i], p=all[i-1]; energy+=x*x; if(p<=0 && x>0) z.push_back(i-1-p/(x-p)); }
            double hz=z.size()>1 ? sr*(z.size()-1)/(z.back()-z.front()) : 0;
            std::cout<<"mode="<<mode<<" offset="<<offset<<" hz="<<hz<<" rms="<<std::sqrt(energy/(b-a-1))<<" crossings="<<z.size()<<'\n';
            const double expected = offset>=4096 && offset<=36000 ? f*ratio : f;
            if (!std::isfinite(hz) || z.size()<10 || std::abs(1200*std::log2(hz/expected))>5) ok=false;
        }
        std::vector<double> crossing;
        for (int i=start-1024;i<start+10000;++i) {
            double x=all[i], p=all[i-1];
            if(p<=0 && x>0) crossing.push_back(i-1-p/(x-p));
        }
        const double base=sr/f, shifted=sr/(f*ratio), middle=(base+shifted)*0.5;
        double first=-1;
        for (size_t i=1;i<crossing.size();++i)
            if(crossing[i]>=start && crossing[i]-crossing[i-1]>=middle) {first=crossing[i]; break;}
        std::cout<<"block="<<block<<" latency_samples="<<latency<<" mode="<<mode<<" step_midpoint_ms="<<(first<0?-1:(first-start)*1000/sr)
                 <<" nominal_latency_ms="<<latency*1000/sr<<'\n';
        if(first<start || first>start+latency+4800) ok=false;
    }
    std::cout << (ok ? "PASS" : "FAIL") << ": steady pitch and bounded step observed; not an Artist-equivalence test\n";
    return ok ? 0 : 1;
}
