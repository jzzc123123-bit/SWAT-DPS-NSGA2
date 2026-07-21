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
      integer :: irbf, jdim, kout
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
      
      !===== read DPS parameters from command line only =====
      narg = command_argument_count()

      if (narg /= 92) then
        write(*,*) 'ERROR: DPS requires exactly 92 command-line arguments.'
        write(*,*) 'Order: a(1:3), w(1:8,1:3), c(1:8,1:4), r(1:8,1:4), job_id'
        stop
      end if

      iarg = 1

!----- read a(kout)
      do kout = 1, dps_kout
        call get_command_argument(iarg, arg)
        read(arg,*,iostat=ios) dps_a(kout)
        if (ios /= 0) stop 'ERROR reading dps_a'
        iarg = iarg + 1
      end do

!----- read w(irbf,kout)
      do irbf = 1, dps_nrbf
        do kout = 1, dps_kout
          call get_command_argument(iarg, arg)
          read(arg,*,iostat=ios) dps_w(irbf,kout)
          if (ios /= 0) stop 'ERROR reading dps_w'
          iarg = iarg + 1
        end do
      end do

!----- read c(irbf,jdim)
      do irbf = 1, dps_nrbf
        do jdim = 1, dps_bdim
          call get_command_argument(iarg, arg)
          read(arg,*,iostat=ios) dps_c(irbf,jdim)
          if (ios /= 0) stop 'ERROR reading dps_c'
          iarg = iarg + 1
        end do
      end do

!----- read r(irbf,jdim)
      do irbf = 1, dps_nrbf
        do jdim = 1, dps_bdim
          call get_command_argument(iarg, arg)
          read(arg,*,iostat=ios) dps_r(irbf,jdim)
          if (ios /= 0) stop 'ERROR reading dps_r'
          iarg = iarg + 1
        end do
      end do

!----- read job_id
      call get_command_argument(iarg, arg)
      read(arg,*,iostat=ios) dps_job_id
      if (ios /= 0) stop 'ERROR reading dps_job_id'

      dps_ready = 1

      write(*,*) 'DPS parameters loaded from command line'
      write(*,*) 'MAIN dps_job_id = ', dps_job_id
      write(*,*) 'MAIN dps_a = ', dps_a(1), dps_a(2), dps_a(3)
      write(*,*) 'MAIN dps_w(1,:) = ', dps_w(1,1), dps_w(1,2), dps_w(1,3)
      write(*,*) 'MAIN dps_c(1,:) = ', dps_c(1,1), dps_c(1,2), dps_c(1,3), dps_c(1,4)
      write(*,*) 'MAIN dps_r(1,:) = ', dps_r(1,1), dps_r(1,2), dps_r(1,3), dps_r(1,4)
!===== end read DPS parameters from command line =====
      
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