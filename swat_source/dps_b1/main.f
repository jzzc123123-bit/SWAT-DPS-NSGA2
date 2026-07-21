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
      integer :: narg, ios
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

      if (narg /= 29) then
        write(*,*) 'ERROR: DPS requires exactly 11 command-line arguments.'
        write(*,*) 'Usage:'
        write(*,*) 'SWAT664.exe 29 job_id'
        stop
      end if

      call get_command_argument(1, arg)
      read(arg,*,iostat=ios) dps_a(1)
      if (ios /= 0) stop 'ERROR reading arg1: dps_a'
      
      call get_command_argument(2, arg)
      read(arg,*,iostat=ios) dps_a(2)
      if (ios /= 0) stop 'ERROR reading arg1: dps_a'

      call get_command_argument(3, arg)
      read(arg,*,iostat=ios) dps_a(3)
      if (ios /= 0) stop 'ERROR reading arg1: dps_a'
      
      call get_command_argument(4, arg)
      read(arg,*,iostat=ios) dps_c(1)
      if (ios /= 0) stop 'ERROR reading arg2: dps_c(1)'

      call get_command_argument(5, arg)
      read(arg,*,iostat=ios) dps_c(2)
      if (ios /= 0) stop 'ERROR reading arg3: dps_c(2)'

      call get_command_argument(6, arg)
      read(arg,*,iostat=ios) dps_c(3)
      if (ios /= 0) stop 'ERROR reading arg4: dps_c(3)'

      call get_command_argument(7, arg)
      read(arg,*,iostat=ios) dps_c(4)
      if (ios /= 0) stop 'ERROR reading arg4: dps_c(3)'
      
      call get_command_argument(8, arg)
      read(arg,*,iostat=ios) dps_c(5)
      if (ios /= 0) stop 'ERROR reading arg4: dps_c(3)'

      call get_command_argument(9, arg)
      read(arg,*,iostat=ios) dps_w(1,1)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'

      call get_command_argument(10, arg)
      read(arg,*,iostat=ios) dps_w(2,1)
      if (ios /= 0) stop 'ERROR reading arg6: dps_w(2)'

      call get_command_argument(11, arg)
      read(arg,*,iostat=ios) dps_w(3,1)
      if (ios /= 0) stop 'ERROR reading arg7: dps_w(3)'
      
      call get_command_argument(12, arg)
      read(arg,*,iostat=ios) dps_w(4,1)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(13, arg)
      read(arg,*,iostat=ios) dps_w(5,1)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(14, arg)
      read(arg,*,iostat=ios) dps_w(2,1)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(15, arg)
      read(arg,*,iostat=ios) dps_w(2,2)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(16, arg)
      read(arg,*,iostat=ios) dps_w(2,3)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(17, arg)
      read(arg,*,iostat=ios) dps_w(2,4)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(18, arg)
      read(arg,*,iostat=ios) dps_w(2,5)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(19, arg)
      read(arg,*,iostat=ios) dps_w(3,1)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(20, arg)
      read(arg,*,iostat=ios) dps_w(3,2)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(21, arg)
      read(arg,*,iostat=ios) dps_w(3,3)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(22, arg)
      read(arg,*,iostat=ios) dps_w(3,4)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(23, arg)
      read(arg,*,iostat=ios) dps_w(3,5)
      if (ios /= 0) stop 'ERROR reading arg5: dps_w(1)'
      
      call get_command_argument(24, arg)
      read(arg,*,iostat=ios) dps_r(1)
      if (ios /= 0) stop 'ERROR reading arg8: dps_r(1)'

      call get_command_argument(25, arg)
      read(arg,*,iostat=ios) dps_r(2)
      if (ios /= 0) stop 'ERROR reading arg9: dps_r(2)'

      call get_command_argument(26, arg)
      read(arg,*,iostat=ios) dps_r(3)
      if (ios /= 0) stop 'ERROR reading arg10: dps_r(3)'
      
      call get_command_argument(27, arg)
      read(arg,*,iostat=ios) dps_r(4)
      if (ios /= 0) stop 'ERROR reading arg10: dps_r(3)'
      
      call get_command_argument(28, arg)
      read(arg,*,iostat=ios) dps_r(5)
      if (ios /= 0) stop 'ERROR reading arg10: dps_r(3)'
      
      call get_command_argument(29, arg)
      read(arg,*,iostat=ios) dps_job_id
      if (ios /= 0) stop 'ERROR reading arg11: dps_job_id'

      dps_ready = 1

      write(*,*) 'DPS parameters loaded from command line'
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