       subroutine globalenergy(
     1  maxlig,maxatom,totmaxatom,maxmode,maxdof,
     2	cartstatehandle, ministatehandle,
     3  phi,ssi,rot,xa,ya,za,dlig,seed,
     4  iab,iori,itra,ieig,fixre,energies, delta)

       implicit none
       
c      Parameters
       integer maxlig,maxatom,totmaxatom,maxmode,maxdof
       integer cartstatehandle,ministatehandle
       integer iab,iori,itra,ieig,fixre,seed
       real*8 energies(6)
       real*8 delta(maxdof)

       real*8 phi, ssi, rot, dlig, xa, ya, za
       dimension phi(maxlig), ssi(maxlig), rot(maxlig)
       dimension dlig(maxlig, maxmode)
       dimension xa(maxlig), ya(maxlig), za(maxlig)

c      Handle variables: cartstate ligand
       real*8 xl(3*maxatom), fl(3*maxatom)
       pointer(ptr_xl,xl)
       pointer(ptr_fl,fl)

c      Handle variables: full coordinates and modes
       integer nlig,nall,nall3
       real*8 xb,xold,x,xori,xori0,f,eig, val,pivot
       integer ieins,nhm,natom,iaci_old
       dimension xb(3*totmaxatom),x(3*totmaxatom),f(3*totmaxatom)
       dimension xold(3*totmaxatom)
       dimension xori(3*totmaxatom),xori0(3*totmaxatom)
       dimension eig(maxlig,maxmode,3*maxatom)
       dimension val(maxlig,maxmode)
       dimension ieins(maxlig),nhm(maxlig)
       dimension pivot(maxlig,3)
       dimension natom(maxlig)
       dimension iaci_old(maxlig)
       pointer(ptr_xb,xb)
       pointer(ptr_x,x)
       pointer(ptr_xori,xori)
       pointer(ptr_xori0,xori0)       
       pointer(ptr_f, f)
       pointer(ptr_eig,eig)
       pointer(ptr_val,val)
       pointer(ptr_ieins,ieins)
       pointer(ptr_nhm,nhm)
       pointer(ptr_pivot,pivot)
       pointer(ptr_natom,natom)
       pointer(ptr_iaci_old,iaci_old)
       
       
c      Local variables   
       integer i,ii,n,jl,jb  
       real*8 cdelta(6+maxmode), rotmat(9)
       real*8 enligl,xnull
       real*8 pm2(3,3,3)
       integer has_globalenergy
       
c      Is global energy used at all?
       call ministate_has_globalenergy(ministatehandle, 
     1  has_globalenergy)

       if (has_globalenergy.eq.1) then
c reset forces
       call reset_forces(cartstatehandle)
  
c get parameters      
       call cartstate_f_globalenergy(cartstatehandle,
     1  nlig, nall, nall3, ptr_nhm,ptr_ieins,
     2  ptr_eig, ptr_val, ptr_xb, ptr_x, ptr_xori, ptr_xori0, 
     3  ptr_f,ptr_pivot, ptr_natom, ptr_iaci_old)      
      
       jl=3*iori*(nlig-fixre)
       jb=3*iori*(nlig-fixre)+3*itra*(nlig-fixre)

c apply normal mode deformations
       do 5 i=1, nlig
       call deform(maxlig,3*maxatom,3*totmaxatom,maxatom,maxmode,
     1  dlig(i,:),nhm,i-1,ieins,eig,xb,x,xori,xori0)
5      continue

       xold(1:nall3) = x(1:nall3)
c       call memcpy(xold,x,nall3*8)
       
       do 6 i=1, nlig
       call euler2rotmat(phi(i),ssi(i),rot(i),rotmat)
       call rotate(maxlig,3*totmaxatom,rotmat,xa(i),ya(i),za(i),pivot,
     1  i-1,ieins,x)
6      continue

c       write(*,'(a2,3f8.3)'), 'G',x(3*902+1),x(3*902+2),x(3*902+3)
c       write(*,'(a2,3f8.3)'), 'G',x(3*1454+1),x(3*1454+2),x(3*1454+3)
c       write(*,*),(x(3*902+1)-x(3*1454+1))* (x(3*902+1)-x(3*1454+1))+ 
c     1  (x(3*902+2)-x(3*1454+2))* (x(3*902+2)-x(3*1454+2)) +
c     2  (x(3*902+3)-x(3*1454+3))* (x(3*902+3)-x(3*1454+3))
c       stop

       call restrain(ministatehandle,cartstatehandle,seed,
     1  iab,energies(3))
       call emenergy(energies(6),nall,x,iaci_old,f,iab)

       x(1:nall3) = xold(1:nall3)
c       call memcpy(x,xold,nall3*8)

c calculate DOF deltas
       do 10 i=1, nlig

       xnull = 0.0d0   
       do 2 ii=1,6+maxmode
       cdelta(ii) = xnull
2      continue  
       
       call cartstate_select_ligand2(cartstatehandle,i-1,ptr_xl,ptr_fl)  
          
       if ((iori.eq.1).AND.(i.gt.fixre)) then
c       write(*,'(a4,i3,f8.3,f8.3,f8.3,f8.3,f8.3,f8.3)'),
c     1  'DOFS',i,phi(i),ssi(i),rot(i),xa(i),ya(i),za(i)
       call euler2torquemat(phi(i),ssi(i),rot(i),pm2)
       call rota(3*maxatom,maxdof,
     1  xl,fl,cdelta,pm2,natom(i))       
       ii = 3 * (i-fixre-1)
       delta(ii+1) = delta(ii+1) + cdelta(1)
       delta(ii+2) = delta(ii+2) + cdelta(2)
       delta(ii+3) = delta(ii+3) + cdelta(3)
       endif             

       if ((itra.eq.1).AND.(i.gt.fixre)) then
       call trans(3*maxatom,maxdof,fl,cdelta,natom(i))       
       ii = jl + 3 * (i-fixre-1)
       delta(ii+1) = delta(ii+1) + cdelta(4)
       delta(ii+2) = delta(ii+2) + cdelta(5)
       delta(ii+3) = delta(ii+3) + cdelta(6)
       endif

c       write(*,*),'DELTA',i,cdelta(1),cdelta(2),cdelta(3),
c     1  cdelta(4),cdelta(5),cdelta(6)
       
       if (ieig.eq.1) then       

       call ligmin(maxlig,maxdof,maxmode,maxatom,
     1  fl,natom(i),i-1,eig,nhm(i),cdelta)

       ii = jb
       do 113 n=1,i-1
       ii = ii + nhm(n)
113    continue  
               
       call moderest(maxdof,maxmode,dlig(i,:),nhm(i),val(i,:),
     1  cdelta, energies(3))
	
       ii = jb
       do 13 n=1,i-1
       ii = ii + nhm(n)
13     continue  
       do 14 n=1,nhm(i)  
       delta(ii+n) = delta(ii+n) + cdelta(6+n)
14     continue
       endif

       
10     continue      
c      end if (has_globalenergy)
       endif 
       call disre(maxlig,cartstatehandle,ministatehandle,
     1  iab,iori,itra,fixre,xa,ya,za,delta,energies(3))


       end