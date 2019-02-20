<#
         Datera VMware Best Practices Implementation Script

=====================================================================
|                          Disclaimer:                              |
| This scripts are offered "as is" with no warranty.  While this    |
| scripts is tested and working in my environment, it is            |
| recommended that you test this script in a test lab before using  |
| in a production environment. Everyone can use the scripts/commands|
| provided here without any written permission but I will not be    |
| liable for any damage or loss to the system.                      |
=====================================================================

Requirements:
1. PowerCLI connection to a Windows vCenter server that manages
   ESXi hosts that must have privileges to make changes to advanced
   settings
2. Before running, please make sure each segment's configuration
   changes as it relates to your environment.
#>

########
########  User Input Section
########
Param(
    [Parameter(Mandatory=$false)]
    [switch]$Confirm = $false,

    [Parameter(Mandatory=$false)]
    [switch]$AllHosts = $false
)

## That means script output tells user what is happening throughout
## the script.
$verbose = $true

## That means no confirmation received for the command to change
## the advanced settings

## Before you run this script, you have to make sure all ESXi hosts
## must be actively managed by Windows vCenter server.
$vmhosts = Get-VMhost
<#
PowerCLI C:\Users\Administrator\ghg> $vmhosts = Get-VMhost
PowerCLI C:\Users\Administrator\ghg> Write-Output $vmhosts

Name                 ConnectionState PowerState NumCpu CpuUsageMhz CpuTotalMhz   MemoryUsageGB   MemoryTotalGB Version
----                 --------------- ---------- ------ ----------- -----------   -------------   ------------- -------
tlx192.tlx.datera... Connected       PoweredOn      16        1089       38384          27.479         127.895   6.0.0
tlx191.tlx.datera... Connected       PoweredOn      16         193       38384           3.350         127.895   6.0.0
#>

########
########    Script
########

if($verbose = $true){
Write-Output "
          _________
         /     ___ \
        /     |___\ \
       |      |____| |
       |      |____| |
        \     |___/ /
         \_________/

   Datera VMware Best Practices
       Configuration Script

"
}

Write-Output "====== List current ESXi hosts managed by vCenter ======"
Write-Output $vmhosts
Write-Output " "


########
########    Fix 1: ATS heartbeat
########

<#
1 | Disable ATS Heartbeat on each ESXi host
Alternate method of implementation:
    esxcli system settings advanced set -i 0 -o /VMFS3/UseATSForHBOnVMFS5

For details, please refer to https://kb.vmware.com/s/article/2113956
#>


Write-Output ("Disable ATS heartbeat on all ESXi hosts, otherwise iSCSI will malfunction")

Foreach($esx in $vmhosts){

    $ats = Get-AdvancedSetting -Entity $esx -Name VMFS3.UseATSForHBOnVMFS5
    If ($Confirm) {
        $ats | Set-AdvancedSetting -Value 0 -Confirm:$false
        if($verbose = $true){
            Write-Output "ATS heartbeat is disabled for " + $esx.name
        }
    } Else {
        Write-Output "Existing ATS Settings: $esx -- $ats"
    }
}

########
########  The following change can interrupt service for iSCSI targets on ESXi
########

########
########    Fix 2: Queue Depth
########

<#
2 | Set Queue Depth for Software iSCSI initiator to 32
Default value is 128 or 256
Datera recommended value is 32
Alternate method of implementation:
    esxcli system module parameters set -m iscsi_vmk -p iscsivmk_LunQDepth=32
#>


Write-Output "
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !!                                                       !!
    !! This script doesn't run on the ESXi host that has     !!
    !! iSCSI target in case you run this script by mistake   !!
    !!                                                       !!
    !! You have two choices:                                 !!
    !! 1.  Remove iSCSI targets from dynamic discovery and   !!
    !!     static target                                     !!
    !!     Re-run this script again after clean them up      !!
    !! 2.  If you really want to run this script no matter   !!
    !!     what, you know what you're doing and it may cause !!
    !!     system misfunction you may run this script        !!
    !!     with the -Confirm flag                            !!
    !!                                                       !!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"
If (($AllHosts -eq $true) -and ($Confirm -eq $true)) {
    Write-output "WARNING: Running on all hosts even with iSCSI targets"
    $hostsToBeExecuted = $vmhosts
} Else {
    $hostsToBeExecuted = @()
    Foreach ($esx in $vmhosts) {
        $IscsiHba = $esx | Get-VMHostHba -Type iScsi | Where {$_.Model -eq "iSCSI Software Adapter"}
        $IscsiTarget = Get-IScsiHbaTarget -IScsiHba $IscsiHba
        If ($IscsiTarget -eq $null) {
            $hostsToBeExecuted +=  $esx
        }
    }
    Write-Output "====== List ESXi hosts without iSCSI target that we can run this script ======"
    Write-Output $hostsToBeExecuted
    Write-Output " "
}

$DateraIscsiQueueDepth = 32
If ($Confirm) {
    Foreach ($esx in $hostsToBeExecuted){
        $esxcli = get-esxcli -VMHost $esx

        If ($esx.Version.Split(".")[0] -ge "6"){
            #vSphere 6.x or greater
            $esxcli.system.module.parameters.set($null, $null,"iscsi_vmk","iscsivmk_LunQDepth=$DateraIscsiQueueDepth")
        } Else {
            #vSphere 5.x command
            $esxcli.system.module.parameters.set($null,"iscsi_vmk","iscsivmk_LunQDepth=$DateraIscsiQueueDepth")
        }

        $esxcli.system.module.parameters.list("iscsi_vmk") | Where{$_.Name -eq "iscsivmk_LunQDepth"}
        If ($verbose = $true){
            Write-Output ("Queue depth for " + $esx.Name + " is set to $DateraIscsiQueueDepth")
        }
    }
}

########
########    Option 3: DelayedAck
########

<#
3 | Turn Off DelayedAck for Random Workloads
Default application value is 1 (Enabled)
Modified application value is 0 (Disabled)

Alternate method of implementation:
    export iscsi_if=`esxcli iscsi adapter list | grep iscsi_vmk | awk '{ print $1 }'`
    vmkiscsi-tool $iscsi_if -W -a delayed_ack=0

    export iscsi_if=`esxcli iscsi adapter list | grep iscsi_vmk | awk '{ print $1 }'`
    vmkiscsi-tool -W $iscsi_if
    or
    vmkiscsid --dump-db | grep Delayed
For details, please refer to https://kb.vmware.com/s/article/1002598
#>

Foreach($esx in $hostsToBeExecuted){
    $view = Get-VMHost $esx | Get-View
    $StorageSystemId = $view.configmanager.StorageSystem
    $IscsiSWAdapterHbaId = ($view.config.storagedevice.HostBusAdapter | where {$_.Model -match "iSCSI Software"}).device

    $options = New-Object VMWare.Vim.HostInternetScsiHbaParamValue[](1)
    $options[0] = New-Object VMware.Vim.HostInternetScsiHbaParamValue
    $options[0].key = "DelayedAck"
    $options[0].value = $false

    $StorageSystem = Get-View -ID $StorageSystemId
    If($verbose) {
        Write-Output "StorageSystem: $StorageSystem"
    }
    If ($Confirm) {
        $StorageSystem.UpdateInternetScsiAdvancedOptions($IscsiSWAdapterHbaId, $null, $options)

        If ($verbose = $true){
            Write-Output "Disable DelayedAck of Software iSCSI adapter on " + $esx.name
        }
    }
}


########
########    Option 4: SATP Rule
########

<#
4 | Create Custom SATP Rule for DATERA

Alternate method of implementation:
esxcli storage nmp satp rule add -s VMW_SATP_DEFAULT_AA -P VMW_PSP_RR -O iops=1 -V DATERA -e "DATERA custom SATP rule"
add(boolean boot,
    string claimoption,
    string description,
    string device,
    string driver,
    boolean force,
    string model,
    string option,
    string psp,
    string pspoption,
    string satp,
    string transport,
    string type,
    string vendor)
    -s = The SATP for which a new rule will be added
    -P = Set the default PSP for the SATP claim rule
    -O = Set the PSP options for the SATP claim rule (option=string
    -V = Set the vendor string when adding SATP claim rules. Vendor/Model rules are mutually exclusive with driver rules (vendor=string)
    -M = Set the model string when adding SATP claim rule.
    -e = Claim rule description

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!! Configuration changes take effect after rebooting ESXI hosts            !!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

To remove the claim rule:
esxcli storage nmp satp rule remove -s VMW_SATP_DEFAULT_AA -P VMW_PSP_RR -O iops=1 -V DATERA -e "DATERA custom SATP rule"
esxcli storage nmp satp rule list
#>

Foreach($esx in $hostsToBeExecuted){
    $esxcliv2=Get-Esxcli -VMHost $esx -v2
    if ($Confirm) {
        $SatpArgs = $esxcliv2.storage.nmp.satp.rule.remove.createArgs()
        $SatpArgs.description = "DATERA custom SATP Rule"
        $SatpArgs.vendor = "DATERA"
        $SatpArgs.satp = "VMW_SATP_ALUA"
        $SatpArgs.psp = "VMW_PSP_RR"
        $SatpArgs.pspoption = "iops=1"
        $result=$esxcliv2.storage.nmp.satp.rule.add.invoke($SatpArgs)

        If ($result){
            Write-Output ("DATERA custom SATP rule [RR, iops=1] is created for " + $esx.name)
        }
    }
}

If ($Confirm) {
    If ($verbose = $true){
    Write-Output "

        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        !!                                                                !!
        !!  Configuration changes take effect after rebooting ESXI hosts  !!
        !!  Please move ESXi host to maintenance mode, then reboot them   !!
        !!                                                                !!
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    "
    }
} Else {
    Write-Output "No changes were made.  To make changes, re-run with -Confirm"

}

<# Result Looks like:
ClaimOptions :
DefaultPSP   : VMW_PSP_RR
Description  : DATERA custom SATP rule
Device       :
Driver       :
Model        :
Name         : VMW_SATP_DEFAULT_AA
Options      :
PSPOptions   : iops='1'
RuleGroup    : user
Transport    :
Vendor       : DATERA
#>
