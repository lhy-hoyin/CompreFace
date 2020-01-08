import { Injectable } from '@angular/core';
import {OrganizationEnService} from "../../store/organization/organization-entitys.service";
import {getSelectOrganizationId} from "../../store/organization/selectors";
import {Store} from "@ngrx/store";
import {Observable} from "rxjs";
import {Organization} from "../../data/organization";
import {AppState} from "../../store";
import {SetSelectedId} from "../../store/organization/action";
import {ROUTERS_URL} from "../../data/routers-url.variable";
import {Router} from "@angular/router";
import {selectUserInfoState} from "../../store/userInfo/selectors";
import {GetUserInfo} from "../../store/userInfo/action";

@Injectable()
export class OrganizationHeaderService {
  selectedId$: Observable<string | null>;
  user$: Observable<any>;
  selectedId: string | null;
  public organization$: Observable<Organization[]>;

  constructor(private organizationEnService: OrganizationEnService, private store: Store<AppState>, private router: Router) {
    this.store.dispatch(new GetUserInfo());

    this.organization$ = this.organizationEnService.entities$;

    this.selectedId$ = this.store.select(getSelectOrganizationId);
    this.user$ = this.store.select(selectUserInfoState);

    this.selectedId$.subscribe(id => {
      this.selectedId = id;
    });
  }

  select(id: string) {
    this.store.dispatch(new SetSelectedId({selectId: id}));
    this.router.navigate([ROUTERS_URL.ORGANIZATION, id ])
  }

  rename(name: string) {
    this.organizationEnService.update({name, id: this.selectedId})
  }
}
