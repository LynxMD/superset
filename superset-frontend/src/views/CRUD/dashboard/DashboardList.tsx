/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { styled, SupersetClient, t } from '@superset-ui/core';
import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import rison from 'rison';
import { isFeatureEnabled, FeatureFlag } from 'src/featureFlags';
import {
  createFetchRelated,
  createErrorHandler,
  handleDashboardDelete,
} from 'src/views/CRUD/utils';
import { useListViewResource, useFavoriteStatus } from 'src/views/CRUD/hooks';
import ConfirmStatusChange from 'src/components/ConfirmStatusChange';
import SubMenu, { SubMenuProps } from 'src/views/components/SubMenu';
import ListView, {
  ListViewProps,
  Filter,
  Filters,
  FilterOperator,
} from 'src/components/ListView';
import { dangerouslyGetItemDoNotUse } from 'src/utils/localStorageHelpers';
import Owner from 'src/types/Owner';
import withToasts from 'src/components/MessageToasts/withToasts';
import FacePile from 'src/components/FacePile';
import Icons from 'src/components/Icons';
import FaveStar from 'src/components/FaveStar';
import PropertiesModal from 'src/dashboard/components/PropertiesModal';
import { Tooltip } from 'src/components/Tooltip';

import Dashboard from 'src/dashboard/containers/Dashboard';
import CertifiedBadge from 'src/components/CertifiedBadge';
import DashboardCard from './DashboardCard';
import { DashboardStatus } from './types';

const PAGE_SIZE = 25;

interface DashboardListProps {
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
  user: {
    userId: string | number;
    firstName: string;
    lastName: string;
  };
}

interface Dashboard {
  changed_by_name: string;
  changed_by_url: string;
  changed_on_delta_humanized: string;
  changed_by: string;
  dashboard_title: string;
  id: number;
  published: boolean;
  url: string;
  thumbnail_url: string;
  owners: Owner[];
  created_by: object;
}

const Actions = styled.div`
  color: ${({ theme }) => theme.colors.grayscale.base};
`;

function DashboardList(props: DashboardListProps) {
  const { addDangerToast, addSuccessToast } = props;

  const {
    state: {
      loading,
      resourceCount: dashboardCount,
      resourceCollection: dashboards,
      bulkSelectEnabled,
    },
    setResourceCollection: setDashboards,
    hasPerm,
    fetchData,
    toggleBulkSelect,
    refreshData,
  } = useListViewResource<Dashboard>(
    'dashboard',
    t('dashboard'),
    addDangerToast,
  );
  const dashboardIds = useMemo(() => dashboards.map(d => d.id), [dashboards]);
  const [saveFavoriteStatus, favoriteStatus] = useFavoriteStatus(
    'dashboard',
    dashboardIds,
    addDangerToast,
  );

  const [dashboardToEdit, setDashboardToEdit] = useState<Dashboard | null>(
    null,
  );

  const { userId } = props.user;
  // TODO: Fix usage of localStorage keying on the user id
  const userKey = dangerouslyGetItemDoNotUse(userId?.toString(), null);

  const canCreate = hasPerm('can_write');
  const canEdit = hasPerm('can_write');
  const canDelete = hasPerm('can_write');

  const initialSort = [{ id: 'changed_on_delta_humanized', desc: true }];

  function openDashboardEditModal(dashboard: Dashboard) {
    setDashboardToEdit(dashboard);
  }

  function handleDashboardEdit(edits: Dashboard) {
    return SupersetClient.get({
      endpoint: `/api/v1/dashboard/${edits.id}`,
    }).then(
      ({ json = {} }) => {
        setDashboards(
          dashboards.map(dashboard => {
            if (dashboard.id === json?.result?.id) {
              const {
                changed_by_name,
                changed_by_url,
                changed_by,
                dashboard_title = '',
                slug = '',
                json_metadata = '',
                changed_on_delta_humanized,
                url = '',
                certified_by = '',
                certification_details = '',
              } = json.result;
              return {
                ...dashboard,
                changed_by_name,
                changed_by_url,
                changed_by,
                dashboard_title,
                slug,
                json_metadata,
                changed_on_delta_humanized,
                url,
                certified_by,
                certification_details,
              };
            }
            return dashboard;
          }),
        );
      },
      createErrorHandler(errMsg =>
        addDangerToast(
          t('An error occurred while fetching dashboards: %s', errMsg),
        ),
      ),
    );
  }

  function handleBulkDashboardDelete(dashboardsToDelete: Dashboard[]) {
    return SupersetClient.delete({
      endpoint: `/api/v1/dashboard/?q=${rison.encode(
        dashboardsToDelete.map(({ id }) => id),
      )}`,
    }).then(
      ({ json = {} }) => {
        refreshData();
        addSuccessToast(json.message);
      },
      createErrorHandler(errMsg =>
        addDangerToast(
          t('There was an issue deleting the selected dashboards: ', errMsg),
        ),
      ),
    );
  }

  const columns = useMemo(
    () => [
      ...(props.user.userId
        ? [
            {
              Cell: ({
                row: {
                  original: { id },
                },
              }: any) => (
                <FaveStar
                  itemId={id}
                  saveFaveStar={saveFavoriteStatus}
                  isStarred={favoriteStatus[id]}
                />
              ),
              Header: '',
              id: 'id',
              disableSortBy: true,
              size: 'xs',
            },
          ]
        : []),
      {
        Cell: ({
          row: {
            original: {
              url,
              dashboard_title: dashboardTitle,
              certified_by: certifiedBy,
              certification_details: certificationDetails,
            },
          },
        }: any) => (
          <Link to={url}>
            {certifiedBy && (
              <>
                <CertifiedBadge
                  certifiedBy={certifiedBy}
                  details={certificationDetails}
                />{' '}
              </>
            )}
            {dashboardTitle}
          </Link>
        ),
        Header: t('Title'),
        accessor: 'dashboard_title',
      },

      {
        Cell: ({
          row: {
            original: { changed_by_name: changedByName },
          },
        }: any) => `${changedByName}`,
        Header: t('Modified by'),
        accessor: 'changed_by.first_name',
        size: 'xl',
      },
      {
        Cell: ({
          row: {
            original: { status },
          },
        }: any) =>
          status === DashboardStatus.PUBLISHED ? t('Published') : t('Draft'),
        Header: t('Status'),
        accessor: 'published',
        size: 'xl',
      },
      {
        Cell: ({
          row: {
            original: { changed_on_delta_humanized: changedOn },
          },
        }: any) => <span className="no-wrap">{changedOn}</span>,
        Header: t('Modified'),
        accessor: 'changed_on_delta_humanized',
        size: 'xl',
      },
      {
        Cell: ({
          row: {
            original: { created_by: createdBy },
          },
        }: any) =>
          createdBy ? `${createdBy.first_name} ${createdBy.last_name}` : '',
        Header: t('Created by'),
        accessor: 'created_by',
        disableSortBy: true,
        size: 'xl',
      },
      {
        Cell: ({
          row: {
            original: { owners = [] },
          },
        }: any) => <FacePile users={owners} />,
        Header: t('Owners'),
        accessor: 'owners',
        disableSortBy: true,
        size: 'xl',
      },
      {
        Cell: ({ row: { original } }: any) => {
          const handleDelete = () =>
            handleDashboardDelete(
              original,
              refreshData,
              addSuccessToast,
              addDangerToast,
            );
          const handleEdit = () => openDashboardEditModal(original);

          return (
            <Actions className="actions">
              {canDelete && (
                <ConfirmStatusChange
                  title={t('Please confirm')}
                  description={
                    <>
                      {t('Are you sure you want to delete')}{' '}
                      <b>{original.dashboard_title}</b>?
                    </>
                  }
                  onConfirm={handleDelete}
                >
                  {confirmDelete => (
                    <Tooltip
                      id="delete-action-tooltip"
                      title={t('Delete')}
                      placement="bottom"
                    >
                      <span
                        role="button"
                        tabIndex={0}
                        className="action-button"
                        onClick={confirmDelete}
                      >
                        <Icons.Trash data-test="dashboard-list-trash-icon" />
                      </span>
                    </Tooltip>
                  )}
                </ConfirmStatusChange>
              )}
              {canEdit && (
                <Tooltip
                  id="edit-action-tooltip"
                  title={t('Edit')}
                  placement="bottom"
                >
                  <span
                    role="button"
                    tabIndex={0}
                    className="action-button"
                    onClick={handleEdit}
                  >
                    <Icons.EditAlt data-test="edit-alt" />
                  </span>
                </Tooltip>
              )}
            </Actions>
          );
        },
        Header: t('Actions'),
        id: 'actions',
        hidden: !canEdit && !canDelete,
        disableSortBy: true,
      },
    ],
    [canEdit, canDelete, ...(props.user.userId ? [favoriteStatus] : [])],
  );

  const favoritesFilter: Filter = useMemo(
    () => ({
      Header: t('Favorite'),
      id: 'id',
      urlDisplay: 'favorite',
      input: 'select',
      operator: FilterOperator.dashboardIsFav,
      unfilteredLabel: t('Any'),
      selects: [
        { label: t('Yes'), value: true },
        { label: t('No'), value: false },
      ],
    }),
    [],
  );

  const filters: Filters = useMemo(
    () => [
      {
        Header: t('Owner'),
        id: 'owners',
        input: 'select',
        operator: FilterOperator.relationManyMany,
        unfilteredLabel: t('All'),
        fetchSelects: createFetchRelated(
          'dashboard',
          'owners',
          createErrorHandler(errMsg =>
            addDangerToast(
              t(
                'An error occurred while fetching dashboard owner values: %s',
                errMsg,
              ),
            ),
          ),
          props.user,
        ),
        paginate: true,
      },
      {
        Header: t('Created by'),
        id: 'created_by',
        input: 'select',
        operator: FilterOperator.relationOneMany,
        unfilteredLabel: t('All'),
        fetchSelects: createFetchRelated(
          'dashboard',
          'created_by',
          createErrorHandler(errMsg =>
            addDangerToast(
              t(
                'An error occurred while fetching dashboard created by values: %s',
                errMsg,
              ),
            ),
          ),
          props.user,
        ),
        paginate: true,
      },
      {
        Header: t('Status'),
        id: 'published',
        input: 'select',
        operator: FilterOperator.equals,
        unfilteredLabel: t('Any'),
        selects: [
          { label: t('Published'), value: true },
          { label: t('Draft'), value: false },
        ],
      },
      ...(props.user.userId ? [favoritesFilter] : []),
      {
        Header: t('Certified'),
        id: 'id',
        urlDisplay: 'certified',
        input: 'select',
        operator: FilterOperator.dashboardIsCertified,
        unfilteredLabel: t('Any'),
        selects: [
          { label: t('Yes'), value: true },
          { label: t('No'), value: false },
        ],
      },
      {
        Header: t('Search'),
        id: 'dashboard_title',
        input: 'search',
        operator: FilterOperator.titleOrSlug,
      },
    ],
    [addDangerToast, favoritesFilter, props.user],
  );

  const sortTypes = [
    {
      desc: false,
      id: 'dashboard_title',
      label: t('Alphabetical'),
      value: 'alphabetical',
    },
    {
      desc: true,
      id: 'changed_on_delta_humanized',
      label: t('Recently modified'),
      value: 'recently_modified',
    },
    {
      desc: false,
      id: 'changed_on_delta_humanized',
      label: t('Least recently modified'),
      value: 'least_recently_modified',
    },
  ];

  function renderCard(dashboard: Dashboard) {
    return (
      <DashboardCard
        dashboard={dashboard}
        hasPerm={hasPerm}
        bulkSelectEnabled={bulkSelectEnabled}
        refreshData={refreshData}
        showThumbnails={
          userKey
            ? userKey.thumbnails
            : isFeatureEnabled(FeatureFlag.THUMBNAILS)
        }
        loading={loading}
        addDangerToast={addDangerToast}
        addSuccessToast={addSuccessToast}
        openDashboardEditModal={openDashboardEditModal}
        saveFavoriteStatus={saveFavoriteStatus}
        favoriteStatus={favoriteStatus[dashboard.id]}
      />
    );
  }

  const subMenuButtons: SubMenuProps['buttons'] = [];
  if (canCreate) {
    subMenuButtons.push({
      name: (
        <>
          <i className="fa fa-plus" /> {t('Dashboard')}
        </>
      ),
      buttonStyle: 'primary',
      onClick: () => {
        window.location.assign('/dashboard/new');
      },
    });
  }
  return (
    <>
      <SubMenu name={t('Dashboards')} buttons={subMenuButtons} />
      <ConfirmStatusChange
        title={t('Please confirm')}
        description={t(
          'Are you sure you want to delete the selected dashboards?',
        )}
        onConfirm={handleBulkDashboardDelete}
      >
        {confirmDelete => {
          const bulkActions: ListViewProps['bulkActions'] = [];
          if (canDelete) {
            bulkActions.push({
              key: 'delete',
              name: t('Delete'),
              type: 'danger',
              onSelect: confirmDelete,
            });
          }
          return (
            <>
              {dashboardToEdit && (
                <PropertiesModal
                  dashboardId={dashboardToEdit.id}
                  show
                  onHide={() => setDashboardToEdit(null)}
                  onSubmit={handleDashboardEdit}
                />
              )}
              <ListView<Dashboard>
                bulkActions={bulkActions}
                bulkSelectEnabled={bulkSelectEnabled}
                cardSortSelectOptions={sortTypes}
                className="dashboard-list-view"
                columns={columns}
                count={dashboardCount}
                data={dashboards}
                disableBulkSelect={toggleBulkSelect}
                fetchData={fetchData}
                filters={filters}
                initialSort={initialSort}
                loading={loading}
                pageSize={PAGE_SIZE}
                showThumbnails={
                  userKey
                    ? userKey.thumbnails
                    : isFeatureEnabled(FeatureFlag.THUMBNAILS)
                }
                renderCard={renderCard}
                defaultViewMode={
                  isFeatureEnabled(FeatureFlag.LISTVIEWS_DEFAULT_CARD_VIEW)
                    ? 'card'
                    : 'table'
                }
              />
            </>
          );
        }}
      </ConfirmStatusChange>
    </>
  );
}

export default withToasts(DashboardList);
