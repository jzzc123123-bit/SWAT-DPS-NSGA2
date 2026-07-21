      subroutine writea
      
!!    ~ ~ ~ PURPOSE ~ ~ ~
!!    this subroutine writes annual output

!!    ~ ~ ~ INCOMING VARIABLES ~ ~ ~
!!    name        |units         |definition
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
!!    bio_yrms(:) |metric tons/ha|annual biomass (dry weight) in the HRU
!!    ch_d(:)     |m             |average depth of main channel
!!    ch_s(2,:)   |m/m           |average slope of main channel
!!    ch_w(2,:)   |m             |average width of main channel
!!    curyr       |none          |current year of simulation (consecutive)
!!    hrupest(:)  |none          |pesticide use flag:
!!                               | 0: no pesticides used in HRU
!!                               | 1: pesticides used in HRU
!!    hrupsty(:,1,:)|mg pst      |amount of pesticide type in surface runoff
!!                               |contribution to stream from HRU during year
!!                               |(in solution)
!!    hrupsty(:,2,:)|mg pst      |amount of pesticide type in surface runoff
!!                               |contribution to stream from HRU during year
!!                               |(sorbed to sediment)
!!    hruyro(:,:) |varies        |HRU annual output array
!!    i           |julian date   |current day of simulation
!!    id1         |julian date   |first day of simulation in current year
!!    ideg        |none          |channel degredation code
!!                               |0: do not compute channel degradation
!!                               |1: compute channel degredation (downcutting
!!                               |   and widening)
!!    iprint      |none          |print code:
!!                               |0 monthly
!!                               |1 daily
!!                               |2 annually
!!    isproj      |none          |special project code:
!!                               |1 test rewind (run simulation twice)
!!    iyr         |year          |current year of simulation (eg 1980)
!!    lai_yrmx(:) |none          |maximum leaf area index for the year in the
!!                               |HRU
!!    i_mo        |none          |month of next day of simulation
!!    mo_chk      |none          |month of current day of simulation
!!    nhru        |none          |number of HRUs in watershed
!!    npmx        |none          |number of different pesticides used in
!!                               |the simulation
!!    nres        |none          |total number of reservoirs in the
!!                               |watershed
!!    nyskip      |none          |number of years to skip output summarization
!!                               |and printing
!!    rchyro(:,:) |varies        |reach annual output array
!!    res_seci(:) |m             |secchi-disk depth
!!    res_vol(:)  |m^3 H2O       |reservoir volume
!!    resouty(1,:)|m^3/s         |flow into reservoir during year
!!    resouty(2,:)|m^3/s         |flow out of reservoir during year
!!    resouty(3,:)|metric tons   |sediment entering reservoir during year
!!    resouty(4,:)|metric tons   |sediment leaving reservoir during year
!!    resouty(5,:)|mg/L          |sediment concentration in reservoir 
!!                               |during year
!!    resouty(6,:)|mg pst        |pesticide entering reservoir during year
!!    resouty(7,:)|mg pst        |pesticide lost from reservoir through
!!                               |reactions during year
!!    resouty(8,:)|mg pst        |pesticide lost from reservoir through
!!                               |volatilization during year
!!    resouty(9,:)|mg pst        |pesticide moving from water to sediment
!!                               |through settling during year
!!    resouty(10,:)|mg pst        |pesticide moving from sediment to water
!!                               |through resuspension during year
!!    resouty(11,:)|mg pst        |pesticide moving from water to sediment
!!                               |through diffusion during year
!!    resouty(12,:)|mg pst        |pesticide lost from reservoir sediment layer
!!                               |through reactions during year
!!    resouty(13,:)|mg pst        |pesticide lost from reservoir sediment layer
!!                               |through burial during year
!!    resouty(14,:)|mg pst        |pesticide transported out of reservoir during
!!                               |year
!!    resouty(15,:)|mg pst/m^3    |pesticide concentration in reservoir water
!!                               |during year
!!    resouty(16,:)|mg pst/m^3    |pesticide concentration in reservoir sediment
!!                               |layer during year
!!    resouty(17,:)|m^3 H2O       |evaporation from reservoir during year
!!    resouty(18,:)|m^3 H2O       |seepage from reservoir during year
!!    resouty(19,:)|m^3 H2O       |precipitation on reservoir during year
!!    resouty(22,:)|kg N          |organic N entering reservoir during year
!!    resouty(23,:)|kg N          |organic N leaving reservoir during year
!!    resouty(24,:)|kg P          |organic P entering reservoir during year
!!    resouty(25,:)|kg P          |organic P leaving reservoir during year
!!    resouty(26,:)|kg N          |nitrate entering reservoir during year
!!    resouty(27,:)|kg N          |nitrate leaving reservoir during year
!!    resouty(28,:)|kg N          |nitrite entering reservoir during year
!!    resouty(29,:)|kg N          |nitrite leaving reservoir during year
!!    resouty(30,:)|kg N          |ammonia entering reservoir during year
!!    resouty(31,:)|kg N          |ammonia leaving reservoir during year
!!    resouty(32,:)|kg P          |mineral P entering reservoir during year
!!    resouty(33,:)|kg P          |mineral P leaving reservoir during year
!!    resouty(34,:)|kg chla       |chlorophyll-a entering reservoir during year
!!    resouty(35,:)|kg chla       |chlorophyll-a leaving reservoir during year
!!    resouty(36,:)|mg P/L        |organic P concentration in reservoir water
!!                               |during year
!!    resouty(37,:)|mg P/L        |mineral P concentration in reservoir water
!!                               |during year
!!    resouty(38,:)|mg N/L        |organic N concentration in reservoir water
!!                               |during year
!!    resouty(39,:)|mg N/L        |nitrate concentration in reservoir water
!!                               |during year
!!    resouty(40,:)|mg N/L        |nitrite concentration in reservoir water
!!                               |during year
!!    resouty(41,:)|mg N/L        |ammonia concentration in reservoir water
!!                               |during year
!!    subtot      |none          |number of subbasins in watershed
!!    subyro(:,:) |varies        |subbasin annual output array
!!    wshddayo(35)|mm H2O        |amount of water stored in soil profile in
!!                               |watershed at end of day
!!    wshdyro(1)  |mm H2O        |average amount of precipitation in watershed
!!                               |for the year
!!    wshdyro(3)  |mm H2O        |surface runoff in watershed for year
!!    wshdyro(4)  |mm H2O        |lateral flow contribution to streamflow in
!!                               |watershed for year
!!    wshdyro(5)  |mm H2O        |water percolation past bottom of soil profile
!!                               |in watershed for year
!!    wshdyro(6)  |mm H2O        |water yield to streamflow from HRUs in
!!                               |watershed for year
!!    wshdyro(7)  |mm H2O        |actual evapotranspiration in watershed
!!                               |for year
!!    wshdyro(8)  |deg C         |average maximum temperature in watershed for
!!                               |the year
!!    wshdyro(9)  |deg C         |average minimum temperature in watershed for
!!                               |the year
!!    wshdyro(12) |metric tons   |sediment yield from HRUs in watershed for
!!                               |the year
!!    wshdyro(40) |kg N/ha       |organic N loading to stream in watershed for
!!                               |the year
!!    wshdyro(41) |kg P/ha       |organic P loading to stream in watershed for
!!                               |the year
!!    wshdyro(42) |kg N/ha       |nitrate loading to stream in surface runoff
!!                               |in watershed for the year
!!    wshdyro(43) |kg P/ha       |soluble P loading to stream in watershed for
!!                               |the year
!!    wshdyro(44) |kg N/ha       |plant uptake of N in watershed for the year
!!    wshdyro(45) |kg N/ha       |nitrate loading to stream in lateral flow
!!                               |in watershed for the year
!!    wshdyro(46) |kg N/ha       |nitrate percolation past bottom of soil
!!                               |profile in watershed for the year
!!    wshdyro(104)|mm H2O        |groundwater contribution to stream in
!!                               |watershed for the year
!!    wshdyro(108)|mm H2O        |potential evapotranspiration in watershed
!!                               |for the year
!!    wshdyro(109)|mm H2O        |drainage tile flow contribution to stream
!!                               |in watershed for the year
!!    wtryr(:,:)  |varies        |HRU impoundment annual output array
!!    yldanu(:)   |metric tons/ha|annual yield (dry weight) in the HRU
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

!!    ~ ~ ~ OUTGOING VARIABLES ~ ~ ~
!!    name        |units         |definition
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
!!    bio_aams(:) |metric tons/ha|average annual biomass (dry weight) in HRU
!!    hruaao(:,:) |varies        |HRU average annual output array
!!    hrupsta(:,:,:)|varies      |HRU average annual pesticide output array
!!    hrupsty(:,:,:)|varies      |HRU annual pesticide output array
!!    hruyro(:,:) |varies        |HRU annual output array
!!    lai_aamx(:) |none          |average annual maximum leaf area index in
!!                               |HRU
!!    rchaao(:,:) |varies        |reach average annual output array
!!    rchyro(:,:) |varies        |reach annual output array
!!    resouta(:,:)|varies        |reservoir average annual output array
!!    resouty(:,:)|varies        |reservoir annual output array
!!    subaao(:,:) |varies        |subbasin average annual output array
!!    subyro(:,:) |varies        |subbasin annual output array
!!    wshdaao(:)  |varies        |watershed average annual output array
!!    wshdyro(:)  |varies        |watershed annual output array
!!    wtraa(:,:)  |varies        |HRU impoundment average annual output array
!!    wtryr(:,:)  |varies        |HRU impoundment annual output array
!!    yldaa(:)    |metric tons/ha|average annual yield (dry weight) in HRU
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

!!    ~ ~ ~ LOCAL DEFINITIONS ~ ~ ~
!!    name        |units         |definition
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
!!    idlast      |none          |number of days simulated in year
!!    j           |none          |counter
!!    k           |none          |counter
!!    sum         |mg pst        |total pesticide loading for year
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

!!    ~ ~ ~ SUBROUTINES/FUNCTIONS CALLED ~ ~ ~
!!    Intrinsic: Real
!!    SWAT: hruyr, impndyr, subyr, rchyr

!!    ~ ~ ~ ~ ~ ~ END SPECIFICATIONS ~ ~ ~ ~ ~ ~

      use parm

      integer :: j, k, navg, imo_dps
      real*8 :: sum, fac_target, fac_target2, fac_target3, days_next
      
      integer :: irbf, kk
      real*8  :: phi_rbf(dps_nrbf)
      real*8  :: z
      
      real*8 :: lorg_cur, lno3_cur, lnh3_cur,lorg_cur2, lno3_cur2, lnh3_cur2,lorg_cur3, lno3_cur3, lnh3_cur3
      real*8 :: sum_org, sum_no3, sum_nh3,sum_org2, sum_no32, sum_nh32
      real*8 :: org_day_next, no3_day_next, nh3_day_next,org_day_next2, no3_day_next2, nh3_day_next2
      real*8 :: org_day_next3, no3_day_next3, nh3_day_next3
      
      logical :: ex_eval
      character(len=12) :: jid
      character(len=40) :: evalfile

      if (i_mo <= mo_chk .or. (curyr == nbyr .and. i == idal)) then
        !! calculate average annual max and min temperature
        wshdyro(8) = wshdyro(8) / 12.
        wshdyro(9) = wshdyro(9) / 12.

          !! annual write-output.std
          if (iscen == 1) then
          write (26,6300) iyr, wshdyro(1), wshdyro(3), wshdyro(4),      
     &            wshdyro(104), wshdyro(5), wshdyro(109), wshddayo(35), 
     &            wshdyro(7), wshdyro(108), wshdyro(6), wshdyro(12),    
     &            wshdyro(42), wshdyro(45), wshdyro(46), wshdyro(44),   
     &            wshdyro(40), wshdyro(43), wshdyro(41), wshdyro(111)
          else if (isproj == 1) then
          write (19,6300) iyr, wshdyro(1), wshdyro(3), wshdyro(4),      
     &            wshdyro(104), wshdyro(5), wshdyro(109), wshddayo(35), 
     &            wshdyro(7), wshdyro(108), wshdyro(6), wshdyro(12),    
     &            wshdyro(42), wshdyro(45), wshdyro(46), wshdyro(44),   
     &            wshdyro(40), wshdyro(43), wshdyro(41), wshdyro(111)
          endif

          !!write channel degradation data (chan.deg)
          if (ideg == 1) then 
            write (16,780) iyr
            do j = 1, nrch
              write (16,779) j, ch_d(j), ch_w(2,j), ch_s(2,j)
            end do
          end if

        if (iprint /= 1) then
          !! annual write--pesticide output (output.pst) for HRUs
          do j = 1, nhru
            if (hrupest(j) == 1) then
            sum = 0.
            do k = 1, npmx
              sum = sum + hrupsty(k,1,j) + hrupsty(k,2,j)
            end do
            if (sum > 0. .and. iprp == 1) then
                write (30,5100) subnum(j), hruno(j), iyr,               
     &                     (hrupsty(k,1,j), hrupsty(k,2,j), k = 1, npmx)
            end if
            end if
          end do

          !! annual write--HRU output (output.hru)
          call hruyr
          call impndyr

          !! annual write--subbasin output (output.sub)
          call subyr

          !! annual write--reach output (.rch)
          call rchyr
          !===== DPS policy update START =====
           if (dps_ready == 1 .and. curyr > nyskip .and.
     &        curyr < myr) then

              z = dps_z_yr(curyr)     
              do irbf = 1, dps_nrbf
                  phi_rbf(irbf) = exp(-((z - dps_c(irbf))**2) / (dps_r(irbf)**2))
              end do
    
          
              do kk = 1, dps_kout
                  dps_u_raw_yr(curyr+1, kk) = dps_a(kk)
                  do irbf = 1, dps_nrbf
                   dps_u_raw_yr(curyr+1, kk) = dps_u_raw_yr(curyr+1, kk) + 
     &       dps_w(irbf, kk) * phi_rbf(irbf)
                  end do
              end do
          
          
    !           1) 根据当前年状态计算下一年策略
                !dps_u_raw_yr(curyr+1) = dps_a
                !do k = 1, dps_nrbf
                !  dps_u_raw_yr(curyr+1) = dps_u_raw_yr(curyr+1) +
        ! &          dps_w(k) * exp(-((dps_z_yr(curyr)-dps_c(k))**2) /
        ! &          (dps_r(k)**2))
          !      end do

            
            
            
                do kk = 1, dps_kout
                 dps_u_yr(curyr+1, kk) = min(1.d0,
     &                          max(0.d0,dps_u_raw_yr(curyr+1, kk)))
                end do
              
            
              do kk = 1, dps_kout
                  dps_fac_yr(curyr+1,kk) = 0.4d0 + 0.8d0 * dps_u_yr(curyr+1,kk)
                  fac_target  = dps_fac_yr(curyr+1,1)
                  fac_target2 = dps_fac_yr(curyr+1,2)
                  fac_target3 = dps_fac_yr(curyr+1,3)
    !           2) 计算当前年三部分原始年负荷（kg/year）
                lorg_cur = 0.d0
                lno3_cur = 0.d0
                lnh3_cur = 0.d0
            
                lorg_cur2 = 0.d0
                lno3_cur2 = 0.d0
                lnh3_cur2 = 0.d0
                
                lorg_cur3 = 0.d0
                lno3_cur3 = 0.d0
                lnh3_cur3 = 0.d0
              end do 
              
                do imo_dps = 1, 12
                  lorg_cur = lorg_cur +
     &          orgnmon(dps_target_inum1,curyr,imo_dps) *
     &          dfloat(ndays(imo_dps+1) - ndays(imo_dps))

                  lno3_cur = lno3_cur +
     &          no3mon(dps_target_inum1,curyr,imo_dps) *
     &          dfloat(ndays(imo_dps+1) - ndays(imo_dps))

                  lnh3_cur = lnh3_cur +
     &          nh3mon(dps_target_inum1,curyr,imo_dps) *
     &          dfloat(ndays(imo_dps+1) - ndays(imo_dps))
                end do

                do imo_dps = 1, 12
                  lorg_cur2 = lorg_cur2 +
     &          orgnmon(dps_target_inum12,curyr,imo_dps) *
     &          dfloat(ndays(imo_dps+1) - ndays(imo_dps))

                  lno3_cur2 = lno3_cur2 +
     &          no3mon(dps_target_inum12,curyr,imo_dps) *
     &          dfloat(ndays(imo_dps+1) - ndays(imo_dps))

                  lnh3_cur2 = lnh3_cur2 +
     &          nh3mon(dps_target_inum12,curyr,imo_dps) *
     &          dfloat(ndays(imo_dps+1) - ndays(imo_dps))
                end do
            
                do imo_dps = 1, 12
                  lorg_cur3 = lorg_cur3 +
     &          orgnmon(dps_target_inum13,curyr,imo_dps) *
     &          dfloat(ndays(imo_dps+1) - ndays(imo_dps))

                  lno3_cur3 = lno3_cur3 +
     &          no3mon(dps_target_inum13,curyr,imo_dps) *
     &          dfloat(ndays(imo_dps+1) - ndays(imo_dps))

                  lnh3_cur3 = lnh3_cur2 +
     &          nh3mon(dps_target_inum13,curyr,imo_dps) *
     &          dfloat(ndays(imo_dps+1) - ndays(imo_dps))
                end do
            
                dps_lorg_raw_yr(curyr) = lorg_cur
                dps_lno3_raw_yr(curyr) = lno3_cur
                dps_lnh3_raw_yr(curyr) = lnh3_cur
            
                dps_lorg_raw_yr2(curyr) = lorg_cur2
                dps_lno3_raw_yr2(curyr) = lno3_cur2
                dps_lnh3_raw_yr2(curyr) = lnh3_cur2
            
                dps_lorg_raw_yr3(curyr) = lorg_cur3
                dps_lno3_raw_yr3(curyr) = lno3_cur3
                dps_lnh3_raw_yr3(curyr) = lnh3_cur3
    !           3) 计算到当前年为止的累计年均基准负荷
                sum_org = 0.d0
                sum_no3 = 0.d0
                sum_nh3 = 0.d0
                sum_org2 = 0.d0
                sum_no32 = 0.d0
                sum_nh32 = 0.d0
                sum_org3 = 0.d0
                sum_no33 = 0.d0
                sum_nh33 = 0.d0
                navg = 0

                !inum1
                do k = nyskip + 1, curyr
                  if (k >= 1) then
                    sum_org = sum_org + dps_lorg_raw_yr(k)
                    sum_no3 = sum_no3 + dps_lno3_raw_yr(k)
                    sum_nh3 = sum_nh3 + dps_lnh3_raw_yr(k)
                    navg = navg + 1
                  end if
                end do

                if (navg > 0) then
                  dps_lorg_base_yr(curyr+1) = sum_org / dfloat(navg)
                  dps_lno3_base_yr(curyr+1) = sum_no3 / dfloat(navg)
                  dps_lnh3_base_yr(curyr+1) = sum_nh3 / dfloat(navg)
                else
                  dps_lorg_base_yr(curyr+1) = dps_lorg_raw_yr(curyr)
                  dps_lno3_base_yr(curyr+1) = dps_lno3_raw_yr(curyr)
                  dps_lnh3_base_yr(curyr+1) = dps_lnh3_raw_yr(curyr)
                end if
            
                navg = 0

                !inum12
                do k = nyskip + 1, curyr
                  if (k >= 1) then
                    sum_org2 = sum_org2 + dps_lorg_raw_yr2(k)
                    sum_no32 = sum_no32 + dps_lno3_raw_yr2(k)
                    sum_nh32 = sum_nh32 + dps_lnh3_raw_yr2(k)
                    navg = navg + 1
                  end if
                end do

                if (navg > 0) then
                  dps_lorg_base_yr2(curyr+1) = sum_org2 / dfloat(navg)
                  dps_lno3_base_yr2(curyr+1) = sum_no32 / dfloat(navg)
                  dps_lnh3_base_yr2(curyr+1) = sum_nh32 / dfloat(navg)
                else
                  dps_lorg_base_yr2(curyr+1) = dps_lorg_raw_yr2(curyr)
                  dps_lno3_base_yr2(curyr+1) = dps_lno3_raw_yr2(curyr)
                  dps_lnh3_base_yr2(curyr+1) = dps_lnh3_raw_yr2(curyr)
                end if
            
                navg = 0

                !inum13
                do k = nyskip + 1, curyr
                  if (k >= 1) then
                    sum_org3 = sum_org3 + dps_lorg_raw_yr3(k)
                    sum_no33 = sum_no33 + dps_lno3_raw_yr3(k)
                    sum_nh33 = sum_nh33 + dps_lnh3_raw_yr3(k)
                    navg = navg + 1
                  end if
                end do

                if (navg > 0) then
                  dps_lorg_base_yr3(curyr+1) = sum_org3 / dfloat(navg)
                  dps_lno3_base_yr3(curyr+1) = sum_no33 / dfloat(navg)
                  dps_lnh3_base_yr3(curyr+1) = sum_nh33 / dfloat(navg)
                else
                  dps_lorg_base_yr3(curyr+1) = dps_lorg_raw_yr3(curyr)
                  dps_lno3_base_yr3(curyr+1) = dps_lno3_raw_yr3(curyr)
                  dps_lnh3_base_yr3(curyr+1) = dps_lnh3_raw_yr3(curyr)
                end if
            

    !           4) 计算下一年三部分目标年负荷（kg/year）
                dps_lorg_target_yr(curyr+1) =
     &          dps_lorg_base_yr(curyr+1) * fac_target

                dps_lno3_target_yr(curyr+1) =
     &          dps_lno3_base_yr(curyr+1) * fac_target

                dps_lnh3_target_yr(curyr+1) =
     &          dps_lnh3_base_yr(curyr+1) * fac_target
            
            
            
                dps_lorg_target_yr2(curyr+1) =
     &          dps_lorg_base_yr2(curyr+1) * fac_target2

                dps_lno3_target_yr2(curyr+1) =
     &          dps_lno3_base_yr2(curyr+1) * fac_target2

                dps_lnh3_target_yr2(curyr+1) =
     &          dps_lnh3_base_yr2(curyr+1) * fac_target2
            
            
                dps_lorg_target_yr3(curyr+1) =
     &          dps_lorg_base_yr3(curyr+1) * fac_target3

                dps_lno3_target_yr3(curyr+1) =
     &          dps_lno3_base_yr3(curyr+1) * fac_target3

                dps_lnh3_target_yr3(curyr+1) =
     &          dps_lnh3_base_yr3(curyr+1) * fac_target3

    !           5) 不保留月形态，下一年改成全年均匀日输入
                days_next = 365.d0

                org_day_next = dps_lorg_target_yr(curyr+1) / days_next
                no3_day_next = dps_lno3_target_yr(curyr+1) / days_next
                nh3_day_next = dps_lnh3_target_yr(curyr+1) / days_next

                org_day_next2 = dps_lorg_target_yr2(curyr+1) / days_next
                no3_day_next2 = dps_lno3_target_yr2(curyr+1) / days_next
                nh3_day_next2 = dps_lnh3_target_yr2(curyr+1) / days_next
            
            
                org_day_next3 = dps_lorg_target_yr3(curyr+1) / days_next
                no3_day_next3 = dps_lno3_target_yr3(curyr+1) / days_next
                nh3_day_next3 = dps_lnh3_target_yr3(curyr+1) / days_next
            
                do imo_dps = 1, 12
                  orgnmon(dps_target_inum1,curyr+1,imo_dps) = org_day_next
                  no3mon(dps_target_inum1,curyr+1,imo_dps)  = no3_day_next
                  nh3mon(dps_target_inum1,curyr+1,imo_dps)  = nh3_day_next
                  no2mon(dps_target_inum1,curyr+1,imo_dps)  = 0.d0
                end do

                do imo_dps = 1, 12
                  orgnmon(dps_target_inum12,curyr+1,imo_dps) = org_day_next2
                  no3mon(dps_target_inum12,curyr+1,imo_dps)  = no3_day_next2
                  nh3mon(dps_target_inum12,curyr+1,imo_dps)  = nh3_day_next2
                  no2mon(dps_target_inum12,curyr+1,imo_dps)  = 0.d0
                end do

                do imo_dps = 1, 12
                  orgnmon(dps_target_inum13,curyr+1,imo_dps) = org_day_next3
                  no3mon(dps_target_inum13,curyr+1,imo_dps)  = no3_day_next3
                  nh3mon(dps_target_inum13,curyr+1,imo_dps)  = nh3_day_next3
                  no2mon(dps_target_inum13,curyr+1,imo_dps)  = 0.d0
                end do
            
            
                if (dps_debug == 1) then
                  !write(*,*) 'WRITEA DPS: year=', curyr,
        ! &                   ' z=', dps_z_yr(curyr),
        !&                   ' uhat_next=', dps_u_raw_yr(curyr+1),
        ! &                   ' ustar_next=', dps_u_yr(curyr+1,1),
        ! &                   ' fac_next=', dps_fac_yr(curyr+1)

                  write(*,*) 'ORG raw/base/target=',
     &                   dps_lorg_raw_yr(curyr),
     &                   dps_lorg_base_yr(curyr+1),
     &                   dps_lorg_target_yr(curyr+1),
     &                   dps_lorg_raw_yr2(curyr),
     &                   dps_lorg_base_yr2(curyr+1),
     &                   dps_lorg_target_yr2(curyr+1)

                  write(*,*) 'NO3 raw/base/target=',
     &                   dps_lno3_raw_yr(curyr),
     &                   dps_lno3_base_yr(curyr+1),
     &                   dps_lno3_target_yr(curyr+1),
     &                   dps_lno3_raw_yr2(curyr),
     &                   dps_lno3_base_yr2(curyr+1),
     &                   dps_lno3_target_yr2(curyr+1)
                  write(*,*) 'NH3 raw/base/target=',
     &                   dps_lnh3_raw_yr(curyr),
     &                   dps_lnh3_base_yr(curyr+1),
     &                   dps_lnh3_target_yr(curyr+1),
     &                   dps_lnh3_raw_yr2(curyr),
     &                   dps_lnh3_base_yr2(curyr+1),
     &                   dps_lnh3_target_yr2(curyr+1)
                  write(*,*) 'Next-year uniform kg/day =',
     &                   org_day_next, no3_day_next, nh3_day_next,
     &                   org_day_next2, no3_day_next2, nh3_day_next2
                end if
           end if
!===== DPS policy update END =====

!===== write DPS evaluation file =====
          write(jid,'(I10)') dps_job_id
          jid = adjustl(jid)
          evalfile = trim(jid)//'_dps_eval.out'

          inquire(file=trim(evalfile), exist=ex_eval)

          if (.not. ex_eval) then
            open(991, file=trim(evalfile), status='replace',
     &           action='write')
            write(991,'(A)') 'year TNload TNconc z ustar fac'
          else
            open(991, file=trim(evalfile), status='old',
     &           position='append', action='write')
          end if

          write(991,'(I6,1X,9(1PE16.8,1X))') curyr,
     &         dps_tn_out_mass_yr(curyr),
     &         dps_ctn_out_yr(curyr),
     &         dps_z_yr(curyr),
     &         dps_u_yr(curyr+1,1),
     &         dps_u_yr(curyr+1,2),
     &         dps_u_yr(curyr+1,3),
     &         dps_fac_yr(curyr+1,1),
     &         dps_fac_yr(curyr+1,2),
     &         dps_fac_yr(curyr+1,3)
          close(991)
!===== end write DPS evaluation file =====

!         !! annual write--sediment routing (.sed)
          call rsedyr

          idlast = 0
          idlast = i - (id1 - 1)
          do j = 1, nres
            resouty(1,j) = resouty(1,j) / Real(idlast)
            resouty(2,j) = resouty(2,j) / Real(idlast)
            resouty(5,j) = resouty(5,j) / Real(idlast)
            resouty(15,j) = resouty(15,j) / Real(idlast)
            resouty(16,j) = resouty(16,j) / Real(idlast)
            resouty(36,j) = resouty(36,j) / Real(idlast)
            resouty(37,j) = resouty(37,j) / Real(idlast)
            resouty(38,j) = resouty(38,j) / Real(idlast)
            resouty(39,j) = resouty(39,j) / Real(idlast)
            resouty(40,j) = resouty(40,j) / Real(idlast)
            resouty(41,j) = resouty(41,j) / Real(idlast)
            if (iyr >= iyres(j)) then
              if (iscen == 1 .and. isproj == 0) then
              write (8,5800) j, iyr, res_vol(j), resouty(1,j),          
     &                       resouty(2,j), resouty(19,j), resouty(17,j),
     &                       resouty(18,j), resouty(3,j), resouty(4,j), 
     &                       resouty(5,j),                              
     &                       (resouty(k,j), k = 22, 23), resouty(38,j), 
     &                       (resouty(k,j), k = 24, 25), resouty(36,j), 
     &                       (resouty(k,j), k = 26, 27), resouty(39,j), 
     &                       (resouty(k,j), k = 28, 29), resouty(40,j), 
     &                       (resouty(k,j), k = 30, 31), resouty(41,j), 
     &                       (resouty(k,j), k = 32, 33), resouty(37,j), 
     &                       (resouty(k,j), k = 34, 35), res_seci(j),   
     &                       (resouty(k,j), k = 6, 16)
              else if (isproj == 1) then
              write (22,5800) j, iyr, res_vol(j), resouty(1,j),         
     &                       resouty(2,j), resouty(19,j), resouty(17,j),
     &                       resouty(18,j), resouty(3,j), resouty(4,j), 
     &                       resouty(5,j),                              
     &                       (resouty(k,j), k = 22, 23), resouty(38,j), 
     &                       (resouty(k,j), k = 24, 25), resouty(36,j), 
     &                       (resouty(k,j), k = 26, 27), resouty(39,j), 
     &                       (resouty(k,j), k = 28, 29), resouty(40,j), 
     &                       (resouty(k,j), k = 30, 31), resouty(41,j), 
     &                       (resouty(k,j), k = 32, 33), resouty(37,j), 
     &                       (resouty(k,j), k = 34, 35), res_seci(j),   
     &                       (resouty(k,j), k = 6, 16)
              else if (iscen == 1 .and. isproj == 2) then
              write (8,6800) j, iyr, res_vol(j), resouty(1,j),          
     &                       resouty(2,j), resouty(19,j), resouty(17,j),
     &                       resouty(18,j), resouty(3,j), resouty(4,j), 
     &                       resouty(5,j),                              
     &                       (resouty(k,j), k = 22, 23), resouty(38,j), 
     &                       (resouty(k,j), k = 24, 25), resouty(36,j), 
     &                       (resouty(k,j), k = 26, 27), resouty(39,j), 
     &                       (resouty(k,j), k = 28, 29), resouty(40,j), 
     &                       (resouty(k,j), k = 30, 31), resouty(41,j), 
     &                       (resouty(k,j), k = 32, 33), resouty(37,j), 
     &                       (resouty(k,j), k = 34, 35), res_seci(j),   
     &                       (resouty(k,j), k = 6, 16), iyr

              endif
            end if
          end do
        end if

        if (curyr > nyskip) then
          do j = 1, nhru
            bio_aams(j) = bio_aams(j) + bio_yrms(j)
            lai_aamx(j) = lai_aamx(j) + lai_yrmx(j)
            yldaa(j) = yldaa(j) + yldanu(j)
          end do

      
          wshdaao = wshdaao + wshdyro
          wpstaao = wpstaao + wpstyro
          hruaao = hruaao + hruyro
          wtraa = wtraa + wtryr
          subaao = subaao + subyro
          rchaao = rchaao + rchyro
          resouta = resouta + resouty
          hrupsta = hrupsta + hrupsty
        end if

        wshdyro = 0.
        wpstyro = 0.
        hruyro = 0.
        wtryr = 0.
        subyro = 0.
        rchyro = 0.
        resouty = 0.
        hrupsty = 0.

      end if

      return
 777  format (i4,500e12.4)
 779  format (i4,3f12.4)
 780  format (/,' Year End',i5,' Channel Dimensions ',/,' Reach',       
     &         '    Depth (m)','  Width (m)','  Slope (m/m)')
 5100 format (1x,a5,a4,1x,i4,4x,1x,250(e16.4,1x))
 5200 format (/,1x,i4,a4,1x,10f12.2)
 5300 format (1x,i4,a4,1x,10f12.2,/)
 5800 format ('RES   ',i8,1x,i4,41e12.4)
 6800 format ('RES   ',i8,1x,i4,41e12.4,1x,i4)
 6300 format (/i5,15f8.2,1x,5f8.2//)
      end