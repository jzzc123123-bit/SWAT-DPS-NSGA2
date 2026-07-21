      include 'modparm.f'
      program main
!!    this is the main program that reads input, calls the main simulation
!!    model, and writes output.
!!    ~ ~ ~ INCOMING VARIABLES ~ ~ ~
!!    name        |units         |definition
!!         ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ 
!!    date        |NA            |date simulation is performed where leftmost
!!                               |eight characters are set to a value of
!!                               |yyyymmdd, where yyyy is the year, mm is the 
!!                               |month and dd is the day
!!    isproj      |none          |special project code:
!!                               |1 test rewind (run simulation twice)
!!    time        |NA            |time simulation is performed where leftmost
!!                               |ten characters are set to a value of
!!                               |hhmmss.sss, where hh is the hour, mm is the 
!!                               |minutes and ss.sss is the seconds and
!!                               |milliseconds
!!    values(1)   |year          |year simulation is performed
!!    values(2)   |month         |month simulation is performed
!!    values(3)   |day           |day in month simulation is performed
!!    values(4)   |minutes       |time difference with respect to Coordinated
!!                               |Universal Time (ie Greenwich Mean Time)
!!    values(5)   |hour          |hour simulation is performed
!!    values(6)   |minutes       |minute simulation is performed
!!    values(7)   |seconds       |second simulation is performed
!!    values(8)   |milliseconds  |millisecond simulation is performed
!!    zone        |NA            |time difference with respect to Coordinated
!!                               |Universal Time (ie Greenwich Mean Time)
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ 
!!    ~ ~ ~ OUTGOING VARIABLES ~ ~ ~
!!    name        |units         |definition
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ 
!!    prog        |NA            |program name and version
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ 
!!    ~ ~ ~ LOCAL DEFINITIONS ~ ~ ~
!!    name        |units         |definition
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ 
!!    i           |none          |counter
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ 
!!    ~ ~ ~ SUBROUTINES/FUNCTIONS CALLED ~ ~ ~
!!    Intrinsic: date_and_time
!!    SWAT: getallo, allocate_parms, readfile, readfig
!!    SWAT: readbsn, std1, readwwq, readinpt, std2, storeinitial
!!    SWAT: openwth, headout, simulate, finalbal, writeaa, pestw 
!!    ~ ~ ~ ~ ~ ~ END SPECIFICATIONS ~ ~ ~ ~ ~ ~

      use parm
      implicit none
      integer :: narg, ios, iarg
      integer :: it, kout, idx_yr
      character(len=64) :: arg
      prog = "SWAT Dec 23 2016    VER 2016/Rev 664"
      write (*,1000)
 1000 format(1x,"               SWAT2016               ",/,             
     &          "               Rev. 664               ",/,             
     &          "      Soil & Water Assessment Tool    ",/,             
     &          "               PC Version             ",/,             
     &          " Program reading from file.cio . . . executing",/)

!! process input
		
      call getallo
      call allocate_parms
      call readfile
      call readbsn
      call readwwq
      if (fcstyr > 0 .and. fcstday > 0) call readfcst
      call readplant             !! read in the landuse/landcover database
      call readtill              !! read in the tillage database
      call readpest              !! read in the pesticide database
      call readfert              !! read in the fertilizer/nutrient database
      call readurban             !! read in the urban land types database
      call readseptwq            !! read in the septic types database
      call readlup
      call readfig
      call readatmodep
      call readinpt
      
       !===== read direct-control uk(t,k) from command line =====
      narg = command_argument_count()

      if (narg /= 29 * dps_kout + 1) then
        write(*,*) 'ERROR: baseline mode requires exactly ', 29*dps_kout+1, ' command-line arguments.'
        write(*,*) 'Order: uk(1:29,1:dps_kout), job_id'
        stop
      end if

      iarg = 1
      dps_u_yr = 0.0

!----- read uk(it,kout), it = 1..29, kout = 1..dps_kout
!----- map them into dps_u_yr(5:33,kout), because actual use is dps_u_yr(curyr+1,kout)
!----- with curyr = 5..33
      do it = 1, 29
        idx_yr = it + 4     ! it=1 -> year index 5 ; it=30 -> year index 33

        do kout = 1, dps_kout
          call get_command_argument(iarg, arg)
          read(arg,*,iostat=ios) dps_u_yr(idx_yr, kout)
          if (ios /= 0) stop 'ERROR reading dps_u_yr'

          if (dps_u_yr(idx_yr, kout) < 0.0 .or. dps_u_yr(idx_yr, kout) > 1.0) then
            write(*,*) 'ERROR: uk out of bounds at it=', it, ' idx_yr=', idx_yr, ' kout=', kout
            stop
          end if

          iarg = iarg + 1
        end do
      end do

!----- optional fill for unused early slots
      dps_u_yr(0,:) = 0.0
      dps_u_yr(1,:) = 0.0
      dps_u_yr(2,:) = 0.0
      dps_u_yr(3,:) = 0.0
      dps_u_yr(4,:) = 0.0

!----- read job_id
      call get_command_argument(iarg, arg)
      read(arg,*,iostat=ios) dps_job_id
      if (ios /= 0) stop 'ERROR reading dps_job_id'

      dps_ready    = 1

      write(*,*) 'Baseline direct-control uk loaded from command line'
      write(*,*) 'MAIN job_id = ', dps_job_id
      write(*,*) 'u for year-index 5, kout=1: ', dps_u_yr(5,1)
      write(*,*) 'u for year-index 34, kout=dps_kout: ', dps_u_yr(33,dps_kout)
      !===== end read direct-control uk(t,k) =====
      
      call std1
      call std2
      call openwth
      call headout

      !! convert integer to string for output.mgt file
      subnum = ""
      hruno = ""
      do i = 1, mhru
        write (subnum(i),fmt=' (i5.5)') hru_sub(i)
        write (hruno(i),fmt=' (i4.4)') hru_seq(i)  
      end do

      if (isproj == 2) then 
        hi_targ = 0.0
      end if

!! save initial values
      if (isproj == 1) then
        scenario = 2
        call storeinitial
      else if (fcstcycles > 1) then
        scenario =  fcstcycles
        call storeinitial
      else
        scenario = 1
      endif
        if (iclb /= 4) then
      do iscen = 1, scenario

     
        !! simulate watershed processes
        call simulate

        !! perform summary calculations
        call finalbal
        call writeaa
        call pestw

        !!reinitialize for new scenario
        if (scenario > iscen) call rewind_init
      end do
         end if
      do i = 101, 109       !Claire 12/2/09: change 1, 9  to 101, 109.
        close (i)
      end do
      close(124)
      write (*,1001)
 1001 format (/," Execution successfully completed ")
	
        iscen=1
!! file for Mike White to review to ensure simulation executed normally
      open (9999,file='fin.fin')
      write (9999,*) 'Execution successful'
      close (9999)
      
	stop
      end